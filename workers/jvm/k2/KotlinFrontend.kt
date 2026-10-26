@file:OptIn(org.jetbrains.kotlin.analysis.api.KaExperimentalApi::class)
package org.kgmaker.worker

import com.intellij.openapi.util.Disposer
import com.intellij.psi.*
import com.intellij.psi.util.ClassUtil
import com.intellij.psi.util.TypeConversionUtil
import org.jetbrains.kotlin.analysis.api.analyze
import org.jetbrains.kotlin.analysis.api.resolution.successfulFunctionCallOrNull
import org.jetbrains.kotlin.analysis.api.resolution.symbol
import org.jetbrains.kotlin.analysis.api.standalone.buildStandaloneAnalysisAPISession
import org.jetbrains.kotlin.analysis.api.symbols.KaFunctionSymbol
import org.jetbrains.kotlin.analysis.api.symbols.KaNamedFunctionSymbol
import org.jetbrains.kotlin.analysis.api.symbols.KaPropertySymbol
import org.jetbrains.kotlin.analysis.api.symbols.KaClassSymbol
import org.jetbrains.kotlin.analysis.api.symbols.KaValueParameterSymbol
import org.jetbrains.kotlin.analysis.api.annotations.KaAnnotationValue
import org.jetbrains.kotlin.analysis.project.structure.builder.buildKtLibraryModule
import org.jetbrains.kotlin.analysis.project.structure.builder.buildKtSdkModule
import org.jetbrains.kotlin.analysis.project.structure.builder.buildKtSourceModule
import org.jetbrains.kotlin.asJava.toLightMethods
import org.jetbrains.kotlin.asJava.toLightClass
import org.jetbrains.kotlin.config.*
import org.jetbrains.kotlin.platform.jvm.JvmPlatforms
import org.jetbrains.kotlin.psi.*
import java.nio.file.Path

/** FIR-backed Standalone Analysis API 2.1.10. Never invokes the K1 frontend.
 * Only compiler-attributed calls with an unambiguous PSI JVM signature become
 * resolved. Unsupported light methods and source execution semantics stay visible.
 */
class KotlinFrontend(private val state: State) {
    private lateinit var methodLookup: Bytecode
    companion object {
        const val backend = "k2-analysis-api-2.1.10-v1"
        const val compiler = "kotlin-2.1.10-k2-analysis-api"
        val capabilities = listOf("kotlin-2.1-analysis-api-attribution")
        val limitations = listOf("K2 Analysis API is pinned to 2.1.10; unrepresentable JVM signatures remain unresolved.",
        "K2 source CFG, constructor ABI, default-body/coroutine mapping, Kotlin operator/reference/initializer call sites and local/lambda execution are not implemented.")
    }

    private fun loc(element: PsiElement): MutableMap<String, Any?> {
        val file = element.containingFile
        val path = Path.of(file.virtualFile.path).toRealPath()
        val text = state.text(path)
        val start = element.textRange.startOffset
        val end = element.textRange.endOffset
        fun line(offset: Int) = text.take(offset).count { it == '\n' } + 1
        fun column(offset: Int) = offset - text.lastIndexOf('\n', (offset - 1).coerceAtLeast(0))
        return state.location(path, start.toLong(), end.toLong(), line(start), column(start), line(end), column(end))
    }

    private fun descriptor(type: PsiType): String? {
        val erased = TypeConversionUtil.erasure(type)
        if (erased is PsiPrimitiveType) return mapOf("void" to "V", "boolean" to "Z", "byte" to "B",
            "char" to "C", "short" to "S", "int" to "I", "long" to "J", "float" to "F", "double" to "D")[erased.canonicalText]
        if (erased is PsiArrayType) return descriptor(erased.componentType)?.let { "[" + it }
        val klass = (erased as? PsiClassType)?.resolve() ?: return null
        return ClassUtil.getJVMClassName(klass)?.let { "L" + it.replace('.', '/') + ";" }
    }

    private fun method(symbol: KaFunctionSymbol, source: PsiElement? = null): String? {
        // Local and synthesized signatures do not have a unique declaration ABI.
        // Light constructors omit JVM synthetic enclosing-instance parameters.
        // Never publish a guessed constructor descriptor until mapped explicitly.
        if (symbol is org.jetbrains.kotlin.analysis.api.symbols.KaConstructorSymbol) return null
        val psi = symbol.psi ?: return null
        if (psi !is KtNamedFunction && psi !is PsiMethod) return null
        val light = if (psi is PsiMethod) listOf(psi) else psi.toLightMethods()
        val candidates = light.filter { it.parameterList.parametersCount == symbol.valueParameters.size }
        val declaration = candidates.singleOrNull() ?: return null
        val owner = declaration.containingClass?.let { ClassUtil.getJVMClassName(it) } ?: return null
        // Compiler built-ins can have light PSI without a corresponding JVM
        // owner (e.g. Kotlin intrinsic types). Such an owner is not a JVM target.
        val parameters = declaration.parameterList.parameters.map { descriptor(it.type) ?: return null }
        val result = if (declaration.isConstructor) "V" else declaration.returnType?.let(::descriptor) ?: return null
        val name = if (declaration.isConstructor) "<init>" else declaration.name
        val signature = "(" + parameters.joinToString("") + ")" + result
        if (source == null && !methodLookup.hasDeclaredMethod(owner, name, signature)) return null
        val location = source?.let(::loc)
        val identity = state.methodIdentity(owner, name, signature, location)
        val existing = state.symbols[identity]
        // JavaFrontend ran first. A Kotlin reference must not replace Javac's
        // authoritative source declaration, annotations, modifiers or throws.
        if (existing?.get("path")?.toString()?.endsWith(".java") == true) return identity
        val metadata = State.map("compiler_backend", backend, "compiler_version", "2.1.10",
            "jvm_static", declaration.hasModifierProperty(com.intellij.psi.PsiModifier.STATIC),
            "parameter_names", symbol.valueParameters.map { it.name.asString() },
            "parameter_types", declaration.parameterList.parameters.map { it.type.canonicalText },
            "default_arguments", symbol.valueParameters.map { it.hasDefaultValue },
            "suspend", (symbol as? KaNamedFunctionSymbol)?.isSuspend ?: false,
            "inline", (symbol as? KaNamedFunctionSymbol)?.isInline ?: false)
        return state.method(owner, name, signature, location, metadata)
    }

    private data class ResolvedAnnotationValue(val value: Any?, val complete: Boolean)

    private fun annotationValue(value: KaAnnotationValue): ResolvedAnnotationValue = when (value) {
        is KaAnnotationValue.ConstantValue -> ResolvedAnnotationValue(value.value.value, value.value.value != null)
        is KaAnnotationValue.EnumEntryValue -> ResolvedAnnotationValue(value.callableId.toString(), true)
        is KaAnnotationValue.ClassLiteralValue -> value.classId?.asSingleFqName()?.asString()
            ?.let { ResolvedAnnotationValue(it, true) } ?: ResolvedAnnotationValue(null, false)
        is KaAnnotationValue.ArrayValue -> {
            val items = value.values.map(::annotationValue)
            ResolvedAnnotationValue(items.map { it.value }, items.all { it.complete })
        }
        is KaAnnotationValue.NestedAnnotationValue -> {
            val nested = annotationFacts(listOf(value.annotation)).firstOrNull()
            ResolvedAnnotationValue(nested, nested?.get("values_resolved") == true)
        }
        else -> ResolvedAnnotationValue(null, false)
    }

    private fun annotationFacts(annotations: Iterable<org.jetbrains.kotlin.analysis.api.annotations.KaAnnotation>): List<Map<String, Any?>> =
        annotations.mapNotNull { annotation ->
            val name = annotation.classId?.asSingleFqName()?.asString() ?: return@mapNotNull null
            var complete = true
            val pairs = annotation.arguments.map { argument ->
                val resolved = annotationValue(argument.expression)
                if (!resolved.complete) complete = false
                argument.name.asString() to resolved
            }
            val values = pairs.filter { it.second.value != null }.associate { it.first to it.second.value }
            State.map("name", name, "values", values, "values_resolved", complete,
                "use_site_target", annotation.useSiteTarget?.name ?: "NONE")
        }

    private fun psiConstant(value: PsiAnnotationMemberValue): ResolvedAnnotationValue = when (value) {
        is PsiLiteralExpression -> ResolvedAnnotationValue(value.value, value.value != null)
        is PsiReferenceExpression -> when (val resolved = value.resolve()) {
            is PsiEnumConstant -> ResolvedAnnotationValue(resolved.name, true)
            is PsiVariable -> resolved.computeConstantValue().let { ResolvedAnnotationValue(it, it != null) }
            else -> ResolvedAnnotationValue(null, false)
        }
        is PsiArrayInitializerMemberValue -> {
            val items = value.initializers.map(::psiConstant)
            ResolvedAnnotationValue(items.map { it.value }, items.all { it.complete })
        }
        is PsiClassObjectAccessExpression -> value.operand.type?.canonicalText
            ?.let { ResolvedAnnotationValue(it, true) } ?: ResolvedAnnotationValue(null, false)
        is PsiAnnotation -> {
            val nested = psiAnnotationFacts(arrayOf(value), "NESTED").firstOrNull()
            ResolvedAnnotationValue(nested, nested?.get("values_resolved") == true)
        }
        else -> ResolvedAnnotationValue(null, false)
    }

    private fun psiAnnotationFacts(annotations: Array<PsiAnnotation>, target: String): List<Map<String, Any?>> =
        annotations.mapNotNull { annotation ->
            val name = annotation.qualifiedName ?: return@mapNotNull null
            var complete = true
            val pairs = annotation.parameterList.attributes.map { attribute ->
                val key = attribute.name ?: "value"
                val resolved = attribute.value?.let(::psiConstant)
                if (resolved == null || !resolved.complete) complete = false
                key to resolved
            }
            val values = pairs.filter { it.second?.value != null }.associate { it.first to it.second!!.value }
            State.map("name", name, "values", values, "values_resolved", complete, "use_site_target", target)
        }

    private fun lightClass(element: PsiElement): PsiClass? = generateSequence(element.parent) { it.parent }
        .filterIsInstance<KtClassOrObject>().firstOrNull()?.toLightClass()

    private fun lightField(element: PsiElement, name: String): PsiField? = lightClass(element)?.findFieldByName(name, false)

    private fun lightGetter(element: PsiElement, name: String): PsiMethod? {
        val capitalized = name.replaceFirstChar { it.uppercase() }
        val klass = lightClass(element) ?: return null
        return (klass.findMethodsByName("get$capitalized", false) + klass.findMethodsByName("is$capitalized", false))
            .filter { it.parameterList.parametersCount == 0 }.singleOrNull()
    }

    fun analyze(files: List<Path>) {
        if (files.isEmpty()) return
        val disposable = Disposer.newDisposable()
        try {
            methodLookup = Bytecode(state)
            val session = buildStandaloneAnalysisAPISession(disposable) {
                buildKtModuleProvider {
                    platform = JvmPlatforms.defaultJvmPlatform
                    val sdk = addModule(buildKtSdkModule {
                        addBinaryRootsFromJdkHome(Path.of(System.getProperty("java.home")), isJre = false)
                        platform = JvmPlatforms.defaultJvmPlatform
                        libraryName = "JDK"
                    })
                    val libraries = state.classpath.mapIndexed { index, entry ->
                        addModule(buildKtLibraryModule {
                            addBinaryRoot(Path.of(entry["path"].toString()))
                            platform = JvmPlatforms.defaultJvmPlatform
                            libraryName = "classpath-$index"
                        })
                    }
                    addModule(buildKtSourceModule {
                        // Supply individual selected files, never the whole checkout.
                        files.forEach { addSourceRoot(it) }
                        (state.request["sources"] as? List<*>)?.filterIsInstance<String>()
                            ?.filter { it.endsWith(".java") }?.forEach { addSourceRoot(state.root.resolve(it)) }
                        addRegularDependency(sdk)
                        libraries.forEach { addRegularDependency(it) }
                        languageVersionSettings = LanguageVersionSettingsImpl(LanguageVersion.KOTLIN_2_1, ApiVersion.KOTLIN_2_1)
                        platform = JvmPlatforms.defaultJvmPlatform
                        moduleName = state.context["module"].toString()
                    })
                }
            }
            for (file in session.modulesWithFiles.values.flatten().filterIsInstance<KtFile>().sortedBy { it.virtualFilePath }) {
                state.diagnostic("K2_SOURCE_MODEL_PARTIAL",
                    "K2 models named-function declarations, explicit call expressions, type annotations and property use-site metadata; other source execution and framework constructs remain unmodeled", loc(file))
                analyze(file) {
                    file.accept(object : KtTreeVisitorVoid() {
                        override fun visitClassOrObject(declaration: KtClassOrObject) {
                            val symbol = declaration.symbol as? KaClassSymbol
                            val fqName = symbol?.classId?.asSingleFqName()?.asString()
                            if (symbol != null && fqName != null) {
                                val metadata = State.map("annotations", annotationFacts(symbol.annotations),
                                    "kind", when (symbol.classKind.name) {
                                        "INTERFACE" -> "interface"
                                        "ENUM_CLASS" -> "enum"
                                        "ANNOTATION_CLASS" -> "annotation_type"
                                        else -> "class"
                                    }, "compiler_backend", backend, "compiler_version", "2.1.10")
                                metadata["supertypes"] = symbol.superTypes.map { it.toString() }
                                metadata.putAll(loc(declaration))
                                state.type(fqName, loc(declaration), metadata)
                            }
                            super.visitClassOrObject(declaration)
                        }

                        override fun visitProperty(property: KtProperty) {
                            val symbol = property.symbol as? KaPropertySymbol
                            val owner = generateSequence(property.parent) { it.parent }.filterIsInstance<KtClassOrObject>()
                                .firstOrNull()?.let { (it.symbol as? KaClassSymbol)?.classId?.asSingleFqName()?.asString() }
                            if (symbol != null && owner != null) {
                                val field = lightField(property, symbol.name.asString())
                                val getter = lightGetter(property, symbol.name.asString())
                                val sourceType = field?.type?.canonicalText ?: getter?.returnType?.canonicalText ?: symbol.returnType.toString()
                                val signature = field?.let { descriptor(it.type) } ?: getter?.returnType?.let(::descriptor)
                                if (signature != null) {
                                    val location = loc(property)
                                    val annotations = (annotationFacts(symbol.annotations) +
                                        psiAnnotationFacts(field?.annotations ?: emptyArray(), "FIELD") +
                                        psiAnnotationFacts(getter?.annotations ?: emptyArray(), "GET"))
                                        .distinctBy { listOf(it["name"], it["use_site_target"], it["values"]) }
                                    val metadata = State.map("annotations", annotations,
                                        "type", sourceType, "mutable", symbol.isVal.not(),
                                        "has_backing_field", symbol.hasBackingField,
                                        "from_primary_constructor", symbol.isFromPrimaryConstructor,
                                        "compiler_backend", backend, "compiler_version", "2.1.10")
                                    metadata.putAll(location)
                                    state.field(owner, symbol.name.asString(), signature, location, metadata)
                                }
                            }
                            state.diagnostic("K2_PROPERTY_ACCESS_UNSUPPORTED", "Property/accessor execution is unresolved", loc(property))
                            super.visitProperty(property)
                        }

                        override fun visitParameter(parameter: KtParameter) {
                            if (parameter.valOrVarKeyword != null) {
                                val symbol = parameter.symbol as? KaValueParameterSymbol
                                val owner = generateSequence(parameter.parent) { it.parent }.filterIsInstance<KtClassOrObject>()
                                    .firstOrNull()?.let { (it.symbol as? KaClassSymbol)?.classId?.asSingleFqName()?.asString() }
                                val field = lightField(parameter, parameter.name ?: "")
                                val getter = lightGetter(parameter, parameter.name ?: "")
                                val sourceType = field?.type?.canonicalText ?: getter?.returnType?.canonicalText ?: symbol?.returnType?.toString().orEmpty()
                                val signature = field?.let { descriptor(it.type) } ?: getter?.returnType?.let(::descriptor)
                                if (symbol != null && owner != null && signature != null) {
                                    val location = loc(parameter)
                                    val annotations = (annotationFacts(symbol.annotations) +
                                        psiAnnotationFacts(field?.annotations ?: emptyArray(), "FIELD") +
                                        psiAnnotationFacts(getter?.annotations ?: emptyArray(), "GET"))
                                        .distinctBy { listOf(it["name"], it["use_site_target"], it["values"]) }
                                    val metadata = State.map("annotations", annotations,
                                        "type", sourceType, "mutable", parameter.valOrVarKeyword?.text == "var",
                                        "has_backing_field", true, "from_primary_constructor", true,
                                        "compiler_backend", backend, "compiler_version", "2.1.10")
                                    metadata.putAll(location)
                                    state.field(owner, symbol.name.asString(), signature, location, metadata)
                                }
                            }
                            super.visitParameter(parameter)
                        }

                        override fun visitNamedFunction(function: KtNamedFunction) {
                            val symbol = function.symbol as? KaNamedFunctionSymbol
                            val caller = symbol?.let { method(it, function) }
                            if (caller == null) {
                                state.diagnostic("K2_UNSUPPORTED_DECLARATION", "No unambiguous JVM light-method signature", loc(function))
                                return
                            }
                            state.diagnostic("K2_SOURCE_CFG_UNSUPPORTED", "Source CFG is not supplied by this K2 backend", loc(function))
                            function.bodyExpression?.accept(object : KtTreeVisitorVoid() {
                                override fun visitClassOrObject(declaration: KtClassOrObject) {
                                    state.diagnostic("K2_LOCAL_CLASS_BODY_UNSUPPORTED",
                                        "Nested class/object bodies have a separate execution owner and are not attributed to the enclosing function", loc(declaration))
                                }
                                override fun visitObjectLiteralExpression(expression: KtObjectLiteralExpression) {
                                    state.diagnostic("K2_OBJECT_LITERAL_BODY_UNSUPPORTED",
                                        "Object-literal initializer execution is not supplied by this backend", loc(expression))
                                }
                                override fun visitNamedFunction(nested: KtNamedFunction) {
                                    state.diagnostic("K2_LOCAL_FUNCTION_UNSUPPORTED", "Local function execution is unresolved", loc(nested))
                                }
                                override fun visitLambdaExpression(lambda: KtLambdaExpression) {
                                    state.diagnostic("K2_LAMBDA_UNSUPPORTED", "Lambda execution is unresolved", loc(lambda))
                                }
                                override fun visitCallExpression(expression: KtCallExpression) {
                                    super.visitCallExpression(expression)
                                    val call = expression.resolveToCall()?.successfulFunctionCallOrNull()
                                    val targetSymbol = call?.symbol
                                    val target = targetSymbol?.let { method(it, it.psi?.takeIf { p ->
                                        p.containingFile?.virtualFile?.path?.let { value ->
                                            val candidate = Path.of(value).toAbsolutePath().normalize()
                                            candidate in files || (state.request["sources"] as? List<*>)
                                                ?.filterIsInstance<String>()?.any { state.root.resolve(it).normalize() == candidate } == true
                                        } == true
                                    }) }
                                    val reason = if (target == null) "K2_UNRESOLVED_OR_UNSUPPORTED_CALL" else "K2_ANALYSIS_API_RESOLVED"
                                    val id = state.site(caller, loc(expression), target,
                                        if (targetSymbol is org.jetbrains.kotlin.analysis.api.symbols.KaConstructorSymbol) "CONSTRUCTOR" else "CALL",
                                        null, reason)
                                    state.sites.last { it["id"] == id }.apply {
                                        put("compiler_backend", backend); put("compiler_version", "2.1.10")
                                        val psi = targetSymbol?.psi
                                        val declarations = if (psi is PsiMethod) listOf(psi) else (psi as? KtNamedFunction)?.toLightMethods().orEmpty()
                                        val declaration = declarations.singleOrNull { it.parameterList.parametersCount == targetSymbol?.valueParameters?.size }
                                        val receiverExpression = (expression.parent as? KtQualifiedExpression)?.receiverExpression
                                        val actualReceiver = receiverExpression?.expressionType ?: call?.partiallyAppliedSymbol?.dispatchReceiver?.type
                                        val receiverType = actualReceiver as? org.jetbrains.kotlin.analysis.api.types.KaClassType
                                        if (target != null && declaration != null && receiverType != null &&
                                            !declaration.hasModifierProperty(PsiModifier.STATIC) && !declaration.hasModifierProperty(PsiModifier.PRIVATE) &&
                                            !declaration.hasModifierProperty(PsiModifier.FINAL) && declaration.containingClass?.hasModifierProperty(PsiModifier.FINAL) != true &&
                                            (expression.parent as? KtDotQualifiedExpression)?.receiverExpression !is KtSuperExpression) {
                                            val classId = receiverType.classId
                                            val receiver = (classId.packageFqName.asString().replace('.', '/') + "/" +
                                                classId.relativeClassName.asString().replace('.', '$')).trimStart('/')
                                            put("dispatch_kind", if (declaration.containingClass?.isInterface == true) "INTERFACE" else "VIRTUAL")
                                            put("dispatch_receiver", receiver)
                                        } else if (target != null && declaration != null && actualReceiver != null && receiverType == null &&
                                            !declaration.hasModifierProperty(PsiModifier.STATIC) && !declaration.hasModifierProperty(PsiModifier.PRIVATE) &&
                                            !declaration.hasModifierProperty(PsiModifier.FINAL)) {
                                            val boundary="K2_GENERIC_RECEIVER_DISPATCH_UNSUPPORTED"
                                            put("dispatch_completeness_reason", boundary)
                                            state.diagnostic(boundary,"Full generic/intersection receiver constraints are not represented; declared target retained without candidates",loc(expression))
                                        }
                                    }
                                }
                            })
                        }
                    })
                }
            }
        } finally {
            if (::methodLookup.isInitialized) methodLookup.close()
            Disposer.dispose(disposable)
        }
    }
}
