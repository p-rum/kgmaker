@file:Suppress("DEPRECATION", "DEPRECATION_ERROR")
package org.kgmaker.worker

import com.intellij.openapi.util.Disposer
import com.intellij.psi.PsiElement
import java.io.File
import java.nio.file.Path
import org.jetbrains.kotlin.cli.common.CLIConfigurationKeys
import org.jetbrains.kotlin.cli.common.config.addKotlinSourceRoot
import org.jetbrains.kotlin.cli.common.messages.MessageCollector
import org.jetbrains.kotlin.cli.jvm.compiler.EnvironmentConfigFiles
import org.jetbrains.kotlin.cli.jvm.compiler.KotlinCoreEnvironment
import org.jetbrains.kotlin.cli.jvm.compiler.KotlinToJVMBytecodeCompiler
import org.jetbrains.kotlin.cli.jvm.config.addJvmClasspathRoot
import org.jetbrains.kotlin.config.*
import org.jetbrains.kotlin.descriptors.*
import org.jetbrains.kotlin.psi.*
import org.jetbrains.kotlin.resolve.BindingContext
import org.jetbrains.kotlin.resolve.DescriptorToSourceUtils
import org.jetbrains.kotlin.resolve.DescriptorUtils
import org.jetbrains.kotlin.resolve.calls.util.getResolvedCall
import org.jetbrains.kotlin.resolve.constants.*
import org.jetbrains.kotlin.codegen.ClassBuilderMode
import org.jetbrains.kotlin.codegen.state.KotlinTypeMapper

/** Verified compiler-2.1.10 K1 compatibility frontend; language 1.9 subset.
 * Unsupported diagnostics stay visible. Source bodies never use bytecode
 * coroutine state-machine ordering as a replacement for source control flow.
 */
class KotlinFrontend(private val state: State) {
    companion object {
        const val backend = "k1-compat-1"
        const val compiler = "kotlin-2.1.10-k1"
        val capabilities = listOf("kotlin-1.9-compatible-attribution")
        val limitations = listOf("Kotlin frontend is the verified K1 language-1.9 compatibility subset, not full K2 Analysis API.")
    }
    private lateinit var binding: BindingContext
    private lateinit var mapper: KotlinTypeMapper
    private val calls = java.util.IdentityHashMap<PsiElement,String>()
    private val constructorInitializers = java.util.Collections.newSetFromMap(java.util.IdentityHashMap<KtExpression,Boolean>())
    private val sources = HashMap<Path,String>()
    private fun loc(element: PsiElement): MutableMap<String,Any?> {
        val file = element.containingFile as KtFile
        val path = Path.of(file.virtualFilePath).toRealPath()
        val text = sources.getOrPut(path) { state.text(path) }
        val start = element.textRange.startOffset
        val end = element.textRange.endOffset
        fun line(offset: Int)=text.take(offset).count { it=='\n' }+1
        fun column(offset: Int)=offset-(text.lastIndexOf('\n', (offset-1).coerceAtLeast(0)))
        @Suppress("UNCHECKED_CAST")
        return state.location(path,start.toLong(),end.toLong(),line(start),column(start),line(end),column(end)) as MutableMap<String,Any?>
    }
    private fun owner(descriptor: DeclarationDescriptor)=mapper.mapOwner(descriptor).internalName.replace('/','.')
    private fun constant(value: ConstantValue<*>): Any? = when(value) {
        is ArrayValue -> value.value.map(::constant)
        is EnumValue -> value.enumClassId.asSingleFqName().asString()+"."+value.enumEntryName.asString()
        is KClassValue -> when(val type=value.value) {
            is KClassValue.Value.NormalClass -> type.classId.asSingleFqName().asString()
            else -> "UNRESOLVED_CLASS_LITERAL"
        }
        is AnnotationValue -> annotation(value.value)
        else -> value.value
    }
    private fun annotation(value: org.jetbrains.kotlin.descriptors.annotations.AnnotationDescriptor): Map<String,Any?> =
        mapOf("name" to value.fqName?.asString(),"values" to value.allValueArguments.mapKeys { it.key.asString() }.mapValues { constant(it.value) })
    private fun annotations(descriptor: DeclarationDescriptor)=descriptor.annotations.map(::annotation)
    private fun method(descriptor: FunctionDescriptor, element: PsiElement? = null): String {
        val signature=mapper.mapAsmMethod(descriptor)
        val name=if(descriptor is ConstructorDescriptor) "<init>" else signature.name
        val meta=State.map("annotations",annotations(descriptor),"parameter_types",descriptor.valueParameters.map { it.type.toString() },
            "parameter_names",descriptor.valueParameters.map { it.name.asString() },"return_type",descriptor.returnType?.toString(),
            "extension_receiver_type",descriptor.extensionReceiverParameter?.type?.toString(),"suspend",descriptor.isSuspend,"inline",descriptor.isInline,
            "default_arguments",descriptor.valueParameters.map { it.declaresDefaultValue() },"visibility",descriptor.visibility.toString(),
            "modifiers",listOfNotNull(descriptor.visibility.toString(),
                if(descriptor.modality==Modality.FINAL)"final" else null,
                if(descriptor.modality==Modality.ABSTRACT)"abstract" else null,
                if(descriptor.dispatchReceiverParameter==null && descriptor !is ConstructorDescriptor)"static" else null))
        return state.method(owner(descriptor),name,signature.descriptor,element?.let(::loc),meta)
    }
    private fun property(descriptor: PropertyDescriptor, element: PsiElement?=null): String {
        val meta=State.map("annotations",(descriptor.annotations.toList()+descriptor.backingField?.annotations?.toList().orEmpty()).map(::annotation),
            "getter_annotations",descriptor.getter?.annotations?.map(::annotation).orEmpty(),"type",descriptor.type.toString(),
            "nullable_type",descriptor.type.isMarkedNullable,"mutable",descriptor.isVar)
        return state.field(owner(descriptor),descriptor.name.asString(),mapper.mapType(descriptor.type).descriptor,element?.let(::loc),meta)
    }
    fun analyze(files: List<Path>) {
        if(files.isEmpty())return
        val disposable=Disposer.newDisposable()
        try {
            val settings=LanguageVersionSettingsImpl(LanguageVersion.KOTLIN_1_9,ApiVersion.KOTLIN_1_9)
            val configuration=CompilerConfiguration().apply {
                put(CLIConfigurationKeys.MESSAGE_COLLECTOR_KEY,MessageCollector.NONE)
                put(CommonConfigurationKeys.MODULE_NAME,state.context["module"].toString())
                put(CommonConfigurationKeys.LANGUAGE_VERSION_SETTINGS,settings)
                put(JVMConfigurationKeys.JDK_HOME,File(System.getProperty("java.home")))
                files.forEach { addKotlinSourceRoot(it.toString()) }
                state.classpath.forEach { addJvmClasspathRoot(File(it["path"].toString())) }
            }
            val environment=KotlinCoreEnvironment.createForProduction(disposable,configuration,EnvironmentConfigFiles.JVM_CONFIG_FILES)
            val analysis=KotlinToJVMBytecodeCompiler.analyze(environment) ?: error("Kotlin analysis failed")
            binding=analysis.bindingContext
            mapper=KotlinTypeMapper(binding,ClassBuilderMode.FULL,state.context["module"].toString(),settings,false,JvmTarget.JVM_21)
            for(diagnostic in binding.diagnostics.all()) state.diagnostic("KOTLIN_"+diagnostic.factory.name,
                diagnostic.severity.toString()+": "+diagnostic.factory.name,loc(diagnostic.psiElement))
            for(file in environment.getSourceFiles()) {
                val moduleId="source-module:"+state.prefix(state.context)+":"+state.root.relativize(Path.of(file.virtualFilePath).toRealPath()).toString().replace('\\','/')
                val value=State.map("id",moduleId,"name","<module>","kind","module","scope",state.context["scope"],"context_id",state.context["id"])
                value.putAll(loc(file));state.symbols[moduleId]=value
                val visitor=Visitor(moduleId)
                visitor.processFileInitializers(file)
                file.accept(visitor)
            }
        }finally { Disposer.dispose(disposable) }
    }
    private inner class Visitor(private var caller: String): KtTreeVisitorVoid() {
        fun processFileInitializers(file: KtFile) {
            val properties=file.declarations.filterIsInstance<KtProperty>().filter {it.initializer!=null}
            if(properties.isEmpty())return
            val descriptor=properties.firstNotNullOfOrNull {binding[BindingContext.VARIABLE,it] as? PropertyDescriptor}
            if(descriptor==null) {
                state.diagnostic("KOTLIN_FILE_INITIALIZER_CFG_UNSUPPORTED","Top-level property owner is unresolved",loc(file));return
            }
            val old=caller
            try {
                caller=state.method(owner(descriptor),"<clinit>","()V",loc(file),State.map("synthetic_source_mapping","FILE_FACADE_INITIALIZER"))
                val statements=ArrayList<Map<String,Any?>>()
                for(property in properties)property.initializer?.let {initializer->
                    constructorInitializers.add(initializer);initializer.accept(this)
                    val location=loc(initializer)
                    statements.add(State.map("kind","assign","label","top-level property initializer: "+property.name,
                        "path",location["path"],"range",location["range"],"sha256",location["sha256"],"value",ir(initializer)))
                }
                state.bodies.add(State.map("method",caller,"language","kotlin","context_id",state.context["id"],
                    "body",State.map("kind","block","statements",statements)))
            }catch(error:Exception){state.diagnostic("KOTLIN_FILE_INITIALIZER_CFG_UNSUPPORTED",error.message?:"mapping",loc(file))}
            finally{caller=old}
        }
        override fun visitClassOrObject(declaration: KtClassOrObject) {
            val descriptor=binding[BindingContext.CLASS,declaration]
            if(descriptor!=null) {
                val name=mapper.mapClass(descriptor).internalName.replace('/','.')
                state.type(name,loc(declaration),State.map("annotations",annotations(descriptor),"kind",descriptor.kind.toString().lowercase(),
                    "supertypes",descriptor.typeConstructor.supertypes.map { it.toString() },
                    "jvm_superclass",descriptor.typeConstructor.supertypes.firstOrNull { (it.constructor.declarationDescriptor as? ClassDescriptor)?.kind != ClassKind.INTERFACE }?.let { mapper.mapType(it).internalName },
                    "jvm_interfaces",descriptor.typeConstructor.supertypes.filter { (it.constructor.declarationDescriptor as? ClassDescriptor)?.kind == ClassKind.INTERFACE }.map { mapper.mapType(it).internalName },
                    "modifiers",listOfNotNull(descriptor.visibility.toString(),if(descriptor.modality==Modality.FINAL)"final" else null,
                        if(descriptor.modality==Modality.ABSTRACT)"abstract" else null)))
                descriptor.unsubstitutedPrimaryConstructor?.let {constructor->
                    val old=caller
                    try {
                        val constructorElement=if(declaration is KtClass)declaration.primaryConstructor?:declaration else declaration
                        caller=method(constructor,constructorElement)
                        val statements=ArrayList<Map<String,Any?>>()
                        for(member in declaration.declarations)when(member) {
                            is KtProperty -> member.initializer?.let {initializer->
                                constructorInitializers.add(initializer);initializer.accept(this)
                                val location=loc(initializer)
                                statements.add(State.map("kind","assign","label","property initializer: "+member.name,
                                    "path",location["path"],"range",location["range"],"sha256",location["sha256"],"value",ir(initializer)))
                            }
                            is KtClassInitializer -> member.body?.let {body->body.accept(this);statements.add(ir(body))}
                        }
                        if(statements.isNotEmpty())state.bodies.add(State.map("method",caller,"language","kotlin","context_id",state.context["id"],
                            "body",State.map("kind","block","statements",statements)))
                    }catch(error:Exception){state.diagnostic("KOTLIN_PRIMARY_CONSTRUCTOR_CFG_UNSUPPORTED",error.message?:"mapping",loc(declaration))}
                    finally{caller=old}
                }
            }
            super.visitClassOrObject(declaration)
        }
        override fun visitAnonymousInitializer(initializer: KtAnonymousInitializer) {
            // Already visited once above under the primary constructor caller.
        }
        override fun visitNamedFunction(function: KtNamedFunction) {
            val descriptor=binding[BindingContext.FUNCTION,function]
            if(descriptor==null) {
                state.diagnostic("KOTLIN_UNRESOLVED_FUNCTION","No compiler descriptor",loc(function));return
            }
            val old=caller
            try {
                caller=method(descriptor,function)
                super.visitNamedFunction(function)
                function.bodyExpression?.let { state.bodies.add(State.map("method",caller,"language","kotlin","context_id",state.context["id"],
                    "body",if(function.hasBlockBody())ir(it) else State.map("kind","return","value",ir(it)))) }
            }catch(error: Exception) {state.diagnostic("KOTLIN_UNSUPPORTED_MAPPING",error.message?:error.javaClass.name,loc(function))}
            finally{caller=old}
        }
        override fun visitSecondaryConstructor(constructor: KtSecondaryConstructor) {
            val descriptor=binding[BindingContext.CONSTRUCTOR,constructor]
            if(descriptor==null){state.diagnostic("KOTLIN_UNRESOLVED_CONSTRUCTOR","Missing descriptor",loc(constructor));return}
            val old=caller
            try {
                caller=method(descriptor,constructor);super.visitSecondaryConstructor(constructor)
                constructor.bodyExpression?.let {state.bodies.add(State.map("method",caller,"language","kotlin","context_id",state.context["id"],"body",ir(it)))}
            }finally{caller=old}
        }
        override fun visitLambdaExpression(expression: KtLambdaExpression) {
            val old=caller; val location=loc(expression)
            caller="lambda:"+caller+":"+location["sha256"]+":"+expression.textRange.startOffset
            val value=State.map("id",caller,"name","<lambda>","kind","function","identity_stability","SNAPSHOT","scope",state.context["scope"],"context_id",state.context["id"])
            value.putAll(location);state.symbols[caller]=value
            super.visitLambdaExpression(expression)
            expression.bodyExpression?.let {state.bodies.add(State.map("method",caller,"language","kotlin","context_id",state.context["id"],"body",ir(it)))}
            caller=old
        }
        override fun visitProperty(declaration: KtProperty) {
            val descriptor=binding[BindingContext.VARIABLE,declaration]
            if(descriptor is PropertyDescriptor)try {property(descriptor,declaration)} catch(error: Exception){state.diagnostic("KOTLIN_UNSUPPORTED_PROPERTY",error.message?:"mapping",loc(declaration))}
            if(!declaration.isLocal) {
                if(declaration.initializer!=null && declaration.initializer !in constructorInitializers)
                    state.diagnostic("KOTLIN_PROPERTY_INITIALIZER_CFG_UNSUPPORTED","Property initializer is not assigned a guessed constructor caller",loc(declaration.initializer!!))
                if(descriptor is PropertyDescriptor)for(accessor in declaration.accessors) {
                    val accessorDescriptor=if(accessor.isGetter)descriptor.getter else descriptor.setter
                    val body=accessor.bodyExpression
                    if(accessorDescriptor!=null && body!=null) {
                        val old=caller
                        try {
                            caller=method(accessorDescriptor,accessor);body.accept(this)
                            state.bodies.add(State.map("method",caller,"language","kotlin","context_id",state.context["id"],
                                "body",if(accessor.hasBlockBody())ir(body) else State.map("kind","return","value",ir(body))))
                        }catch(error:Exception){state.diagnostic("KOTLIN_UNSUPPORTED_ACCESSOR",error.message?:"mapping",loc(accessor))}
                        finally{caller=old}
                    }
                }
                return
            }
            super.visitProperty(declaration)
        }
        override fun visitParameter(parameter: KtParameter) {
            binding[BindingContext.PRIMARY_CONSTRUCTOR_PARAMETER,parameter]?.let { property(it,parameter) }
            if(parameter.hasDefaultValue()) {
                state.diagnostic("KOTLIN_DEFAULT_ARGUMENT_CFG_UNSUPPORTED","Default argument evaluation is not mapped to a guessed caller",loc(parameter))
                return
            }
            super.visitParameter(parameter)
        }
        override fun visitCallExpression(expression: KtCallExpression) {
            val resolved=expression.getResolvedCall(binding)
            val descriptor=resolved?.resultingDescriptor as? FunctionDescriptor
            var target: String?=null
            var reason="UNRESOLVED_COMPILER_SYMBOL"
            var receiver: String?=null
            if(descriptor!=null)try {
                if(!resolved.status.isSuccess)reason="COMPILER_RESOLUTION_ERROR"
                else {
                    val psi=DescriptorToSourceUtils.descriptorToDeclaration(descriptor)
                    target=method(descriptor,if(psi?.containingFile?.virtualFile?.path?.let { Path.of(it).startsWith(state.root) }==true)psi else null)
                    receiver=resolved.dispatchReceiver?.type?.toString()?:resolved.extensionReceiver?.type?.toString()
                    reason="KOTLIN_COMPILER_RESOLVED_CALL"
                }
            }catch(error: Exception){reason="UNSUPPORTED_SIGNATURE:"+(error.message?:error.javaClass.name)}
            val invocation=if(descriptor is ConstructorDescriptor)"CONSTRUCTOR" else if(descriptor?.extensionReceiverParameter!=null)"EXTENSION" else "CALL"
            val identity=state.site(caller,loc(expression),target,invocation,receiver,reason);calls[expression]=identity
            if(target!=null && descriptor !is ConstructorDescriptor && descriptor?.visibility!=DescriptorVisibilities.PRIVATE && descriptor?.modality!=Modality.FINAL &&
                resolved?.dispatchReceiver!=null && (expression.parent as? KtDotQualifiedExpression)?.receiverExpression !is KtSuperExpression) {
                val type=mapper.mapType(resolved.dispatchReceiver!!.type)
                if(type.sort==org.jetbrains.org.objectweb.asm.Type.OBJECT)state.sites.last().putAll(State.map(
                    "dispatch_kind","VIRTUAL","dispatch_receiver",type.internalName))
            }
            if(target==null)state.diagnostic("KOTLIN_UNRESOLVED_CALL",reason,loc(expression))
            super.visitCallExpression(expression)
        }
        override fun visitBinaryExpression(expression: KtBinaryExpression) {
            val resolved=expression.getResolvedCall(binding)
            val descriptor=resolved?.resultingDescriptor as? FunctionDescriptor
            if(descriptor?.isOperator==true && resolved.status.isSuccess) {
                val psi=DescriptorToSourceUtils.descriptorToDeclaration(descriptor)
                val local=psi?.containingFile?.virtualFile?.path?.let {Path.of(it).startsWith(state.root)}==true
                if(local)try {
                    val target=method(descriptor,psi)
                    calls[expression]=state.site(caller,loc(expression),target,"OPERATOR",
                        resolved.dispatchReceiver?.type?.toString()?:resolved.extensionReceiver?.type?.toString(),
                        "KOTLIN_COMPILER_RESOLVED_OPERATOR")
                }catch(error:Exception){state.diagnostic("KOTLIN_UNRESOLVED_OPERATOR",error.message?:"mapping",loc(expression))}
            }
            super.visitBinaryExpression(expression)
        }
        override fun visitCallableReferenceExpression(expression: KtCallableReferenceExpression) {
            val descriptor=binding[BindingContext.REFERENCE_TARGET,expression.callableReference] as? FunctionDescriptor
            val target=try {descriptor?.let {method(it)}}catch(error: Exception){null}
            state.site(caller,loc(expression),target,"METHOD_REFERENCE",descriptor?.dispatchReceiverParameter?.type?.toString(),
                if(target==null)"UNRESOLVED_METHOD_REFERENCE" else "KOTLIN_RESOLVED_REFERENCE")
            super.visitCallableReferenceExpression(expression)
        }
        override fun visitSimpleNameExpression(expression: KtSimpleNameExpression) {
            val descriptor=binding[BindingContext.REFERENCE_TARGET,expression]
            if(descriptor is PropertyDescriptor)try {
                val psi=DescriptorToSourceUtils.descriptorToDeclaration(descriptor)
                val target=property(descriptor,if(psi?.containingFile?.virtualFile?.path?.let {Path.of(it).startsWith(state.root)}==true)psi else null)
                val parent=expression.parent
                val write=parent is KtBinaryExpression && parent.left==expression && parent.operationToken==org.jetbrains.kotlin.lexer.KtTokens.EQ
                val fact=State.map("kind",if(write)"writes_field" else if(descriptor.isConst)"reads_constant" else "reads_field","source",caller,"target",target,"evidence_kind","SYMBOL_RESOLVED")
                fact.putAll(loc(expression));state.facts.add(fact)
                val accessor=if(write)descriptor.setter else descriptor.getter
                if(expression.getReferencedName()!="field" && accessor!=null) {
                    val accessorPsi=DescriptorToSourceUtils.descriptorToDeclaration(accessor)
                    val local=accessorPsi?.containingFile?.virtualFile?.path?.let {Path.of(it).startsWith(state.root)}==true
                    val accessorTarget=method(accessor,if(local)accessorPsi else null)
                    calls[expression]=state.site(caller,loc(expression),accessorTarget,"ACCESSOR",
                        accessor.dispatchReceiverParameter?.type?.toString(),"KOTLIN_COMPILER_RESOLVED_ACCESSOR")
                }
            }catch(error:Exception){state.diagnostic("KOTLIN_UNRESOLVED_PROPERTY_ACCESS",error.message?:"mapping",loc(expression))}
            super.visitSimpleNameExpression(expression)
        }
    }
    private fun callsIn(element: KtExpression): List<String> {
        val result=ArrayList<String>()
        element.accept(object: KtTreeVisitorVoid() {
            override fun visitLambdaExpression(expression: KtLambdaExpression) {}
            override fun visitNamedFunction(function: KtNamedFunction) {}
            override fun visitCallExpression(expression: KtCallExpression) {calls[expression]?.let(result::add);super.visitCallExpression(expression)}
        })
        return result
    }
    private fun label(element: PsiElement)=element.text.replace(Regex("\"(?:\\\\.|[^\"\\\\])*\""),"\"…\"").take(300)
    fun ir(expression: KtExpression?): Map<String,Any?> {
        if(expression==null)return mapOf("kind" to "empty")
        val base=loc(expression).apply {put("kind","statement");put("label",label(expression));put("calls",callsIn(expression))}
        when(expression) {
            is KtNameReferenceExpression -> {
                val target=binding[BindingContext.REFERENCE_TARGET,expression]
                if(calls.containsKey(expression))base.putAll(mapOf("kind" to "call","call_site" to calls[expression],
                    "arguments" to emptyList<Map<String,Any?>>(),"receiver" to mapOf("kind" to "empty")))
                else if(target is ClassDescriptor || target is PackageViewDescriptor || target is PackageFragmentDescriptor)
                    base.putAll(mapOf("kind" to "reference","calls" to emptyList<String>()))
            }
            is KtCallExpression -> base.putAll(mapOf("kind" to "call","call_site" to calls[expression],
                "arguments" to (expression.valueArguments.map {ir(it.getArgumentExpression())} + expression.lambdaArguments.map {ir(it.getLambdaExpression())}),"receiver" to mapOf("kind" to "empty")))
            is KtDotQualifiedExpression -> {
                val selector=ir(expression.selectorExpression).toMutableMap()
                if(selector["kind"]=="call") {selector["receiver"]=ir(expression.receiverExpression);return selector}
                base.putAll(mapOf("kind" to "sequence","expressions" to listOf(ir(expression.receiverExpression),selector)))
            }
            is KtProperty -> base.putAll(mapOf("kind" to "assign","value" to ir(expression.initializer)))
            is KtLambdaExpression -> base.putAll(mapOf("kind" to "reference","calls" to emptyList<String>()))
            is KtBlockExpression -> {base["kind"]="block";base["statements"]=expression.statements.map(::ir)}
            is KtIfExpression -> base.putAll(mapOf("kind" to "if","condition" to ir(expression.condition),"then" to ir(expression.then),"else" to ir(expression.`else`)))
            is KtWhileExpression -> base.putAll(mapOf("kind" to "while","condition" to ir(expression.condition),"body" to ir(expression.body)))
            is KtDoWhileExpression -> base.putAll(mapOf("kind" to "do","condition" to ir(expression.condition),"body" to ir(expression.body)))
            is KtForExpression -> base.putAll(mapOf("kind" to "foreach","iterable" to ir(expression.loopRange),"body" to ir(expression.body)))
            is KtReturnExpression -> base.putAll(mapOf("kind" to "return","value" to ir(expression.returnedExpression)))
            is KtThrowExpression -> base.putAll(mapOf("kind" to "throw","value" to ir(expression.thrownExpression)))
            is KtBreakExpression -> {base["kind"]="break";if(expression.getLabelName()!=null)base["labelled_target"]=expression.getLabelName()}
            is KtContinueExpression -> {base["kind"]="continue";if(expression.getLabelName()!=null)base["labelled_target"]=expression.getLabelName()}
            is KtTryExpression -> base.putAll(mapOf("kind" to "try","body" to ir(expression.tryBlock),"catches" to expression.catchClauses.map {mapOf("type" to it.catchParameter?.typeReference?.text,"body" to ir(it.catchBody))},"finally" to expression.finallyBlock?.finalExpression?.let(::ir)))
            is KtWhenExpression -> base.putAll(mapOf("kind" to "switch","condition" to ir(expression.subjectExpression),"cases" to expression.entries.map {entry->mapOf("label" to if(entry.isElse)"default" else entry.conditions.joinToString(",") {label(it)},"body" to ir(entry.expression))},"fallthrough" to false))
            is KtParenthesizedExpression -> return ir(expression.expression)
            is KtBinaryExpression -> if(calls.containsKey(expression)) base.putAll(mapOf("kind" to "call",
                "call_site" to calls[expression],"arguments" to listOf(ir(expression.right)),"receiver" to ir(expression.left))) else when(expression.operationToken) {
                org.jetbrains.kotlin.lexer.KtTokens.ANDAND -> base.putAll(mapOf("kind" to "and","left" to ir(expression.left),"right" to ir(expression.right)))
                org.jetbrains.kotlin.lexer.KtTokens.OROR -> base.putAll(mapOf("kind" to "or","left" to ir(expression.left),"right" to ir(expression.right)))
                org.jetbrains.kotlin.lexer.KtTokens.ELVIS -> base.putAll(mapOf("kind" to "elvis","left" to ir(expression.left),"right" to ir(expression.right)))
                org.jetbrains.kotlin.lexer.KtTokens.EQ -> base.putAll(mapOf("kind" to "assign","value" to ir(expression.right),
                    "call_site" to ((expression.left as? KtNameReferenceExpression)?.let {calls[it]})))
                else -> base.putAll(mapOf("kind" to "sequence","expressions" to listOf(ir(expression.left),ir(expression.right))))
            }
            is KtSafeQualifiedExpression -> base.putAll(mapOf("kind" to "safe_call","receiver" to ir(expression.receiverExpression),"then" to ir(expression.selectorExpression)))
            is KtLabeledExpression -> {base["kind"]="unsupported";base["reason"]="LABELLED_CONTROL_FLOW";state.diagnostic("LABELLED_CONTROL_FLOW","No guessed labelled target",loc(expression))}
        }
        return base
    }
}
