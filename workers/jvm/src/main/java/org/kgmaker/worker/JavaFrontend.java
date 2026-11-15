package org.kgmaker.worker;

import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.lang.model.element.*;
import javax.lang.model.type.*;
import javax.lang.model.util.*;
import javax.tools.*;
import java.nio.file.*;
import java.util.*;
import static org.kgmaker.worker.State.map;

/** JavacTask attribution owns target identity; no name index is used. */
public final class JavaFrontend {
    private final State state;
    private Trees trees; private Types types; private Elements elements;
    private SelectorFacts selectorFacts;
    private final Map<Element,Map<String,Object>> bindingCache=new IdentityHashMap<>();
    private RegistrationFacts registrationFacts;
    private CompilationUnitTree unit; private Path file; private String source;
    private final Map<Tree,String> calls = new IdentityHashMap<>();
    private final Map<Tree,String> lambdas = new IdentityHashMap<>();
    private final List<Diagnostic<? extends JavaFileObject>> errors = new ArrayList<>();
    public JavaFrontend(State state){this.state=state;}

    public void analyze(List<Path> sources) throws Exception {
        if(sources.isEmpty())return;
        var compiler=ToolProvider.getSystemJavaCompiler();
        if(compiler==null)throw new IllegalStateException("TOOLCHAIN_UNAVAILABLE:javac");
        var collector=new DiagnosticCollector<JavaFileObject>();
        try(var files=compiler.getStandardFileManager(collector,null,java.nio.charset.StandardCharsets.UTF_8)) {
            String cp=String.join(java.io.File.pathSeparator,state.classpath.stream().map(e->(String)e.get("path")).toList());
            var options=new ArrayList<>(List.of("-proc:none","-classpath",cp,"-implicit:none"));
            if(state.request.get("java_release")!=null)options.addAll(List.of("--release",state.request.get("java_release").toString()));
            var task=(JavacTask)compiler.getTask(null,files,collector,options,null,files.getJavaFileObjectsFromPaths(sources));
            var units=task.parse();task.analyze();trees=Trees.instance(task);types=task.getTypes();elements=task.getElements();
            selectorFacts=new SelectorFacts(types,elements);
            registrationFacts=new RegistrationFacts(trees,types,elements);
            for(var diagnostic:collector.getDiagnostics()) {
                if(diagnostic.getKind()==Diagnostic.Kind.ERROR)errors.add(diagnostic);
                state.diagnostic("JAVAC_"+diagnostic.getCode(),diagnostic.getMessage(Locale.ROOT),null);
            }
            for(var compilation:units) {
                unit=compilation; file=Path.of(unit.getSourceFile().toUri()).toRealPath(); source=state.text(file);
                new Visitor().scan(unit,null);
            }
        }
    }
    private String typeDescriptor(TypeMirror type) {
        type=types.erasure(type);
        return switch(type.getKind()) {
            case BOOLEAN->"Z";case BYTE->"B";case SHORT->"S";case INT->"I";case LONG->"J";
            case CHAR->"C";case FLOAT->"F";case DOUBLE->"D";case VOID->"V";
            case ARRAY->"["+typeDescriptor(((ArrayType)type).getComponentType());
            case DECLARED->"L"+elements.getBinaryName((TypeElement)((DeclaredType)type).asElement()).toString().replace('.','/')+";";
            default->throw new IllegalArgumentException("Unsupported/error JVM type: "+type);
        };
    }
    private String descriptor(ExecutableElement element) {
        String args=String.join("",element.getParameters().stream().map(p->typeDescriptor(p.asType())).toList());
        return "("+args+")"+(element.getKind()==ElementKind.CONSTRUCTOR?"V":typeDescriptor(element.getReturnType()));
    }
    private String owner(Element element) {
        for(Element current=element;current!=null;current=current.getEnclosingElement())
            if(current instanceof TypeElement type)return elements.getBinaryName(type).toString();
        throw new IllegalArgumentException("No binary owner: "+element);
    }
    private Map<String,Object> loc(Tree tree) {
        long start=trees.getSourcePositions().getStartPosition(unit,tree),end=trees.getSourcePositions().getEndPosition(unit,tree);
        var lines=unit.getLineMap();
        return state.location(file,start,end,start<0?0:(int)lines.getLineNumber(start),start<0?0:(int)lines.getColumnNumber(start),
            end<0?0:(int)lines.getLineNumber(end),end<0?0:(int)lines.getColumnNumber(end));
    }
    private Map<String,Object> declarationLocation(Element element) {
        var p=trees.getPath(element);if(p==null)return null;
        var compilation=p.getCompilationUnit();
        try {
            Path target=Path.of(compilation.getSourceFile().toUri()).toRealPath();
            if(!target.startsWith(state.root))return null;
            state.text(target);
            long start=trees.getSourcePositions().getStartPosition(compilation,p.getLeaf()),end=trees.getSourcePositions().getEndPosition(compilation,p.getLeaf());
            var lines=compilation.getLineMap();
            return state.location(target,start,end,start<0?0:(int)lines.getLineNumber(start),start<0?0:(int)lines.getColumnNumber(start),end<0?0:(int)lines.getLineNumber(end),end<0?0:(int)lines.getColumnNumber(end));
        }catch(java.io.IOException error){return null;}
    }
    private String label(Tree tree) {
        // Locations retain original conditions; display strings are not payload storage.
        String value=tree.toString().replaceAll("\"(?:\\\\.|[^\"\\\\])*\"","\"…\"");
        return value.substring(0,Math.min(value.length(),300));
    }
    private Map<String,Object> annotations(Element element) {
        var values=new ArrayList<Map<String,Object>>();
        for(var annotation:element.getAnnotationMirrors()) {
            var members=new LinkedHashMap<String,Object>();
            for(var entry:elements.getElementValuesWithDefaults(annotation).entrySet())
                members.put(entry.getKey().getSimpleName().toString(),annotationValue(entry.getValue().getValue()));
            values.add(map("name",((TypeElement)annotation.getAnnotationType().asElement()).getQualifiedName().toString(),"values",members));
        }
        return map("annotations",values,"modifiers",element.getModifiers().stream().map(Modifier::toString).sorted().toList());
    }
    private Object annotationValue(Object value) {
        if(value instanceof List<?> list)return list.stream().map(v->annotationValue(((AnnotationValue)v).getValue())).toList();
        if(value instanceof VariableElement enumValue)return enumValue.getEnclosingElement()+"."+enumValue.getSimpleName();
        if(value instanceof TypeMirror type)return type.toString();
        if(value instanceof AnnotationMirror nested)return nested.toString();
        return value;
    }
    private boolean errorAt(Tree tree) {
        long begin=trees.getSourcePositions().getStartPosition(unit,tree),end=trees.getSourcePositions().getEndPosition(unit,tree);
        return errors.stream().anyMatch(d->d.getSource()!=null && d.getSource().toUri().equals(unit.getSourceFile().toUri()) &&
            d.getPosition()>=begin && d.getPosition()<=end);
    }
    private String method(ExecutableElement element,Map<String,Object> location) {
        var metadata=annotations(element);
        metadata.put("jvm_static",element.getModifiers().contains(Modifier.STATIC));
        metadata.put("return_type",element.getReturnType().toString());
        metadata.put("parameter_types",element.getParameters().stream().map(p->p.asType().toString()).toList());
        metadata.put("parameter_names",element.getParameters().stream().map(p->p.getSimpleName().toString()).toList());
        metadata.put("throws",element.getThrownTypes().stream().map(TypeMirror::toString).toList());
        return state.method(owner(element),element.getKind()==ElementKind.CONSTRUCTOR?"<init>":element.getSimpleName().toString(),descriptor(element),location,metadata);
    }
    private class Visitor extends TreePathScanner<Void,Void> {
        private String caller;
        @Override public Void visitClass(ClassTree tree,Void unused) {
            Element element=trees.getElement(getCurrentPath());
            if(element instanceof TypeElement type) {
                var metadata=annotations(type);metadata.put("kind",type.getKind().toString().toLowerCase(Locale.ROOT));
                metadata.put("supertypes",types.directSupertypes(type.asType()).stream().map(TypeMirror::toString).toList());
                var contracts=new ArrayList<Map<String,Object>>();
                for(var parent:types.directSupertypes(type.asType())) {
                    if(parent instanceof DeclaredType d && d.asElement() instanceof TypeElement t
                        && Set.of("org.springframework.data.jpa.domain.Specification","com.querydsl.core.types.dsl.EntityPathBase",
                            "org.springframework.data.jpa.repository.JpaRepository","org.springframework.data.repository.CrudRepository",
                            "org.springframework.data.repository.PagingAndSortingRepository","org.springframework.data.repository.Repository").contains(t.getQualifiedName().toString()))
                        contracts.add(map("type",parent.toString(),"symbol",state.type(elements.getBinaryName(t).toString(),declarationLocation(t),null)));
                }
                if(!contracts.isEmpty())metadata.put("query_type_contracts",contracts);
                metadata.put("jvm_interfaces",type.getInterfaces().stream().map(t->elements.getBinaryName((TypeElement)types.asElement(types.erasure(t))).toString().replace('.','/')).toList());
                metadata.put("jvm_superclass",type.getSuperclass().getKind()==TypeKind.NONE?null:elements.getBinaryName((TypeElement)types.asElement(types.erasure(type.getSuperclass()))).toString().replace('.','/'));
                metadata.put("modifiers",type.getModifiers().stream().map(m->m.toString()).toList());
                metadata.putAll(selectorFacts.describe(type));
                metadata.putAll(registrationFacts.describe(type));
                state.type(elements.getBinaryName(type).toString(),loc(tree),metadata);
            }
            return super.visitClass(tree,unused);
        }
        @Override public Void visitMethod(MethodTree tree,Void unused) {
            String old=caller;
            try {
                Element element=trees.getElement(getCurrentPath());
                if(!(element instanceof ExecutableElement executable))return super.visitMethod(tree,unused);
                Map<String,Object> location=loc(tree);
                if(location.get("range")==null)return null; // compiler-generated constructor has no invented source range
                caller=method(executable,location);
                // Only the actual dependency interface override grants Specification
                // intent. A same-name overload (with or without @Override) is not it.
                if(executable.getEnclosingElement() instanceof TypeElement declaring) {
                    for(var parent:types.directSupertypes(declaring.asType())) {
                        if(parent instanceof DeclaredType d && d.asElement() instanceof TypeElement contract
                                && contract.getQualifiedName().contentEquals("org.springframework.data.jpa.domain.Specification")
                                && trees.getPath(contract)==null) {
                            for(var member:contract.getEnclosedElements()) {
                                if(member instanceof ExecutableElement candidate
                                        && candidate.getSimpleName().contentEquals("toPredicate")
                                        && elements.overrides(executable,candidate,declaring))
                                    state.symbols.get(caller).put("query_override",method(candidate,null));
                            }
                        }
                    }
                }
                var literal=selectorFacts.literalReturn(executable,tree,errorAt(tree));
                if(literal!=null)state.symbols.get(caller).put("static_import_return",literal);
                state.symbols.get(caller).putAll(registrationFacts.method(executable,tree,getCurrentPath(),errorAt(tree)));
                super.visitMethod(tree,unused);
                if(tree.getBody()!=null)state.bodies.add(map("method",caller,"language","java","context_id",state.context.get("id"),"return_flow_version",1,"return_body_kind",errorAt(tree)?"ERROR":executable.getKind()==ElementKind.CONSTRUCTOR?"CONSTRUCTOR":"DECLARED","return_type",valueInfo(executable.getReturnType()),"local_operation_version",1,"local_operation_status",executable.getKind()==ElementKind.METHOD&&!errorAt(tree)&&errors.stream().noneMatch(d->d.getSource()!=null&&d.getSource().toUri().equals(unit.getSourceFile().toUri()))?"AVAILABLE":"UNAVAILABLE","query_ir_version",1,"query_ir_status",errors.isEmpty()?"AVAILABLE":"UNAVAILABLE","query_parameters",tree.getParameters().stream().map(this::queryParameter).toList(),"body",ir(tree.getBody())));
                return null;
            }catch(IllegalArgumentException error){state.diagnostic("JAVA_UNSUPPORTED_METHOD_TYPE",error.getMessage(),loc(tree));return null;}
            finally{caller=old;}
        }
        @Override public Void visitLambdaExpression(LambdaExpressionTree tree,Void unused) {
            String old=caller;
            var location=loc(tree);
            String lambda="lambda:"+caller+":"+location.get("sha256")+":"+((Map<?,?>)location.get("range")).get("start");
            var value=map("id",lambda,"name","<lambda>","kind","function","identity_stability","SNAPSHOT","scope",state.context.get("scope"),"context_id",state.context.get("id"));
            value.putAll(location);value.put("query_callable_type",trees.getTypeMirror(getCurrentPath()).toString());
            var callable=types.asElement(trees.getTypeMirror(getCurrentPath()));
            if(callable instanceof TypeElement t)value.put("query_callable_symbol",state.type(elements.getBinaryName(t).toString(),declarationLocation(t),null));state.symbols.put(lambda,value);lambdas.put(tree,lambda);caller=lambda;
            super.visitLambdaExpression(tree,unused);
            state.bodies.add(map("method",lambda,"language","java","context_id",state.context.get("id"),"return_flow_version",1,"return_body_kind","CALLABLE","query_ir_version",1,"query_ir_status",errors.isEmpty()?"AVAILABLE":"UNAVAILABLE","query_parameters",tree.getParameters().stream().map(this::queryParameter).toList(),"body",ir(tree.getBody())));
            caller=old;return null;
        }
        private Map<String,Object> queryParameter(VariableTree tree) {
            var type=trees.getTypeMirror(TreePath.getPath(unit,tree));
            return map("binding",binding(tree),"type",type==null?null:type.toString());
        }
        private void invocation(Tree tree,String kind) {
            if(caller==null)return;
            var location=loc(tree);String dispatchReceiver=null,dispatchBoundary=null;boolean dispatchEligible=false;String target=null,receiver=null,reason="UNRESOLVED_COMPILER_SYMBOL";
            var element=trees.getElement(getCurrentPath());
            if(element instanceof ExecutableElement executable && !errorAt(tree)) try {
                Map<String,Object> targetLoc=declarationLocation(executable);
                dispatchEligible=!executable.getModifiers().contains(Modifier.STATIC) && !executable.getModifiers().contains(Modifier.PRIVATE) && !executable.getModifiers().contains(Modifier.FINAL) && !executable.getEnclosingElement().getModifiers().contains(Modifier.FINAL);
                target=method(executable,targetLoc);receiver=owner(executable);dispatchReceiver=receiver;reason="JAVAC_ATTRIBUTED_SYMBOL";
                if(tree instanceof MethodInvocationTree invocation && invocation.getMethodSelect() instanceof MemberSelectTree select) {
                    var receiverPath=new TreePath(new TreePath(getCurrentPath(),select),select.getExpression());
                    var receiverType=trees.getTypeMirror(receiverPath);if(receiverType!=null){receiver=receiverType.toString();var erased=types.erasure(receiverType);if(erased instanceof DeclaredType declared && declared.asElement() instanceof TypeElement type)dispatchReceiver=elements.getBinaryName(type).toString();else dispatchReceiver=null;}
                    if(dispatchEligible && receiverType!=null && (receiverType.getKind()==TypeKind.TYPEVAR || receiverType.getKind()==TypeKind.INTERSECTION)) {
                        dispatchEligible=false;
                        dispatchBoundary=receiverType.getKind()==TypeKind.TYPEVAR?"JAVA_GENERIC_RECEIVER_DISPATCH_UNSUPPORTED":"JAVA_INTERSECTION_RECEIVER_DISPATCH_UNSUPPORTED";
                    }
                    if((select.getExpression() instanceof IdentifierTree identifier && identifier.getName().contentEquals("super")) ||
                        (select.getExpression() instanceof MemberSelectTree qualifier && qualifier.getIdentifier().contentEquals("super"))) {
                        kind="SPECIAL";dispatchEligible=false;
                    }
                }
                if(executable.getModifiers().contains(Modifier.STATIC))kind="STATIC";
                else if(executable.getModifiers().contains(Modifier.PRIVATE))kind="SPECIAL";
                else if(!kind.equals("SPECIAL") && executable.getEnclosingElement().getKind()==ElementKind.INTERFACE)kind="INTERFACE";
            }catch(IllegalArgumentException error){reason="UNSUPPORTED_SIGNATURE:"+error.getMessage();}
            if(tree instanceof MemberReferenceTree)kind="METHOD_REFERENCE";
            String identity=state.site(caller,location,target,kind,receiver,reason);calls.put(tree,identity);
            if(tree instanceof MethodInvocationTree invocation && element instanceof ExecutableElement executable &&
                    !executable.getModifiers().contains(Modifier.STATIC)) {
                String receiverKind=null,receiverIdentity=null;
                if(invocation.getMethodSelect() instanceof IdentifierTree) {
                    receiverKind="THIS";
                } else if(invocation.getMethodSelect() instanceof MemberSelectTree select) {
                    Tree expression=select.getExpression();
                    if(expression instanceof IdentifierTree identifier && identifier.getName().contentEquals("this") ||
                            expression instanceof MemberSelectTree qualifier && qualifier.getIdentifier().contentEquals("this")) {
                        receiverKind="THIS";
                    } else if(expression instanceof IdentifierTree identifier && identifier.getName().contentEquals("super") ||
                            expression instanceof MemberSelectTree qualifier && qualifier.getIdentifier().contentEquals("super")) {
                        receiverKind="SUPER";
                    } else {
                        var receiverBinding=binding(expression);
                        if(receiverBinding!=null) {
                            receiverKind=(String)receiverBinding.get("kind");
                            Object candidate="FIELD".equals(receiverKind)?receiverBinding.get("symbol"):receiverBinding.get("id");
                            if(candidate instanceof String value)receiverIdentity=value;
                        } else if(expression instanceof NewClassTree)receiverKind="NEW";
                    }
                }
                if(receiverKind!=null) {
                    state.sites.getLast().put("receiver_binding_kind",receiverKind);
                    if(receiverIdentity!=null)state.sites.getLast().put("receiver_binding",receiverIdentity);
                }
            }
            if(target!=null && element instanceof ExecutableElement executable && !(tree instanceof MemberReferenceTree)) {
                List<? extends ExpressionTree> arguments=tree instanceof MethodInvocationTree call?call.getArguments():
                    tree instanceof NewClassTree call?call.getArguments():List.of();
                var parameters=executable.getParameters();boolean completeBinding=true;
                List<? extends TypeMirror> parameterTypes=parameters.stream().map(VariableElement::asType).toList();
                if(tree instanceof MethodInvocationTree call && trees.getTypeMirror(TreePath.getPath(unit,call.getMethodSelect())) instanceof ExecutableType attributed)
                    parameterTypes=attributed.getParameterTypes();
                for(int index=0;index<arguments.size();index++) {
                    int parameterIndex=executable.isVarArgs()?Math.min(index,parameters.size()-1):index;
                    if(parameterIndex<0 || parameterIndex>=parameters.size()) {
                        state.diagnostic("JAVA_ARGUMENT_MAPPING_UNAVAILABLE","Attributed argument has no formal",location);completeBinding=false;break;
                    }
                    String transformation="DIRECT";
                    if(executable.isVarArgs() && parameterIndex==parameters.size()-1) {
                        var argumentType=trees.getTypeMirror(TreePath.getPath(unit,arguments.get(index)));
                        var arrayType=parameterTypes.getLast();
                        if(arrayType instanceof ArrayType array && array.getComponentType().getKind()==TypeKind.TYPEVAR) {
                            completeBinding=false;
                            state.diagnostic("JAVA_VARARG_TRANSFORMATION_UNAVAILABLE","Vararg array packing requires an instantiated formal type",loc(arguments.get(index)));
                            continue;
                        }
                        transformation=arguments.size()==parameters.size() && argumentType!=null &&
                            types.isAssignable(argumentType,arrayType)?"VARARG_ARRAY":"VARARG_ELEMENT";
                    }
                    if(!state.argumentBinding(identity,target,index,parameterIndex,parameters.get(parameterIndex).getSimpleName().toString(),
                        transformation,loc(arguments.get(index)))) {
                        completeBinding=false;state.diagnostic("JAVA_ARGUMENT_MAPPING_UNAVAILABLE","Argument expression locator is unavailable",location);
                    }
                }
                state.bindingStatus(identity,completeBinding,completeBinding?"JAVAC_EXECUTABLE_ARGUMENT_MAPPING":"JAVA_ARGUMENT_MAPPING_UNAVAILABLE");
            }
            if(dispatchEligible && target!=null && dispatchReceiver!=null && Set.of("VIRTUAL","INTERFACE").contains(kind))state.sites.getLast().putAll(map("dispatch_kind",kind,"dispatch_receiver",dispatchReceiver.replace('.','/')));
            if(target!=null && dispatchBoundary!=null && Set.of("VIRTUAL","INTERFACE").contains(kind)) {
                state.sites.getLast().put("dispatch_completeness_reason",dispatchBoundary);
                state.diagnostic(dispatchBoundary,"Full source receiver constraints are not represented; declared target is retained without dispatch candidates",location);
            }
            if(target==null)state.diagnostic("JAVA_UNRESOLVED_CALL",reason,location);
            if(target!=null && (target.contains("java.lang.Class.forName") || target.contains("java.lang.reflect.Method.invoke")))
                state.diagnostic("DYNAMIC_REFLECTION_BOUNDARY","Declared reflection API is resolved; runtime target is unknown",location);
        }
        @Override public Void visitMethodInvocation(MethodInvocationTree tree,Void unused) {invocation(tree,"VIRTUAL");return super.visitMethodInvocation(tree,unused);}
        @Override public Void visitNewClass(NewClassTree tree,Void unused) {invocation(tree,"CONSTRUCTOR");return super.visitNewClass(tree,unused);}
        @Override public Void visitMemberReference(MemberReferenceTree tree,Void unused) {invocation(tree,"METHOD_REFERENCE");return super.visitMemberReference(tree,unused);}
        @Override public Void visitVariable(VariableTree tree,Void unused) {
            var element=trees.getElement(getCurrentPath());
            if(element instanceof VariableElement variable && (variable.getKind()==ElementKind.FIELD || variable.getKind()==ElementKind.ENUM_CONSTANT))try {
                var metadata=fieldMetadata(variable);
                if(variable.getKind()==ElementKind.ENUM_CONSTANT)metadata.put("kind","enum_constant");
                state.field(owner(variable),variable.getSimpleName().toString(),typeDescriptor(variable.asType()),loc(tree),metadata);
                if(tree.getInitializer()!=null){state.diagnostic("JAVA_INITIALIZER_CFG_UNSUPPORTED","Initializer body is not mapped to constructor/class initializer CFG",loc(tree));return null;}
            }catch(IllegalArgumentException error){state.diagnostic("JAVA_UNRESOLVED_FIELD",error.getMessage(),loc(tree));}
            return super.visitVariable(tree,unused);
        }
        @Override public Void visitBlock(BlockTree tree,Void unused) {
            if(caller==null && getCurrentPath().getParentPath().getLeaf() instanceof ClassTree){
                state.diagnostic("JAVA_INITIALIZER_CFG_UNSUPPORTED","Class initializer CFG not mapped",loc(tree));return null;
            }
            return super.visitBlock(tree,unused);
        }
        private void reference(Tree tree) {
            if(caller==null)return;
            var element=trees.getElement(getCurrentPath());
            if(element instanceof VariableElement variable && (variable.getKind()==ElementKind.FIELD || variable.getKind()==ElementKind.ENUM_CONSTANT))try {
                String field=state.field(owner(variable),variable.getSimpleName().toString(),typeDescriptor(variable.asType()),null,annotations(variable));
                Tree parent=getCurrentPath().getParentPath().getLeaf();
                boolean write=(parent instanceof AssignmentTree a&&a.getVariable()==tree)||(parent instanceof CompoundAssignmentTree compound&&compound.getVariable()==tree);
                var fact=map("kind",variable.getKind()==ElementKind.ENUM_CONSTANT?"reads_constant":write?"writes_field":"reads_field","source",caller,"target",field,"evidence_kind","SYMBOL_RESOLVED");
                fact.putAll(loc(tree));state.facts.add(fact);
            }catch(IllegalArgumentException error){state.diagnostic("JAVA_UNRESOLVED_FIELD",error.getMessage(),loc(tree));}
        }
        @Override public Void visitIdentifier(IdentifierTree tree,Void unused){reference(tree);return super.visitIdentifier(tree,unused);}
        @Override public Void visitMemberSelect(MemberSelectTree tree,Void unused){reference(tree);return super.visitMemberSelect(tree,unused);}
    }
    private List<String> callsIn(Tree node) {
        var values=new ArrayList<String>();
        new TreeScanner<Void,Void>() {
            @Override public Void scan(Tree tree,Void unused){if(tree==null)return null;String id=calls.get(tree);if(id!=null && !(tree instanceof MemberReferenceTree))values.add(id);return super.scan(tree,unused);}
            @Override public Void visitLambdaExpression(LambdaExpressionTree tree,Void unused){return null;}
            @Override public Void visitClass(ClassTree tree,Void unused){return null;}
        }.scan(node,null);
        return values;
    }
    /** Bounded source-backed QueryDSL generated member initialization, never a Q-name guess. */
    private Map<String,Object> fieldMetadata(VariableElement variable) {
        var metadata=annotations(variable);metadata.put("type",variable.asType().toString());
        var path=trees.getPath(variable);
        if(path==null || !(path.getLeaf() instanceof VariableTree declaration)
                || !(declaration.getInitializer() instanceof MethodInvocationTree init))return metadata;
        var ownerType=variable.getEnclosingElement();
        if(!(ownerType instanceof TypeElement type))return metadata;
        var bases=types.directSupertypes(type.asType());
        var base=bases.stream().filter(t->t instanceof DeclaredType d &&
            ((TypeElement)d.asElement()).getQualifiedName().contentEquals("com.querydsl.core.types.dsl.EntityPathBase")
            && trees.getPath(d.asElement())==null).findFirst().orElse(null);
        if(!(base instanceof DeclaredType declared) || declared.getTypeArguments().size()!=1)return metadata;
        var target=trees.getElement(new TreePath(path,init));
        if(!(target instanceof ExecutableElement method) || trees.getPath(method)!=null
                || !owner(method).equals("com.querydsl.core.types.dsl.BeanPath")
                || !Set.of("createString","createNumber").contains(method.getSimpleName().toString())
                || init.getArguments().isEmpty() || !(init.getArguments().getFirst() instanceof LiteralTree literal)
                || !(literal.getValue() instanceof String property))return metadata;
        metadata.put("querydsl_path",map("version",1,"entity_type",declared.getTypeArguments().getFirst().toString(),
            "attribute",property,"factory",method(method,null),"factory_owner",owner(method)));
        return metadata;
    }
    private Map<String,Object> valueInfo(TypeMirror type) {
        if(type==null || type.getKind()==TypeKind.ERROR || type.getKind()==TypeKind.NONE)
            return map("version",1,"status","UNKNOWN","type_ref","unknown","nullability","UNKNOWN");
        if(type.getKind()==TypeKind.VOID)
            return map("version",1,"status","VOID","type_ref","V","nullability","UNKNOWN");
        if(type.getKind()==TypeKind.NULL)
            return map("version",1,"status","VALUE","type_ref","null","nullability","NULL_LITERAL");
        try {
            var element=types.asElement(type);
            boolean callable=element instanceof TypeElement t && t.getKind()==ElementKind.INTERFACE && elements.isFunctionalInterface(t);
            return map("version",1,"status",callable?"CALLABLE":"VALUE","type_ref",typeDescriptor(type),
                "nullability",type.getKind().isPrimitive()?"DECLARED_NON_NULL":"UNKNOWN");
        }catch(IllegalArgumentException error){return map("version",1,"status","UNKNOWN","type_ref","unknown","nullability","UNKNOWN");}
    }
    private Map<String,Object> valueInfo(Tree tree) {
        var path=tree==null?null:TreePath.getPath(unit,tree);
        return valueInfo(path==null || errorAt(tree)?null:trees.getTypeMirror(path));
    }
    private Map<String,Object> valueBinding(Tree tree) {
        var path=tree==null?null:TreePath.getPath(unit,tree);
        var element=path==null?null:trees.getElement(path);
        if(!(element instanceof VariableElement variable))return null;
        if(!Set.of(ElementKind.LOCAL_VARIABLE,ElementKind.PARAMETER,ElementKind.FIELD,ElementKind.ENUM_CONSTANT).contains(variable.getKind()))return null;
        var location=declarationLocation(variable);
        if(location==null || !(location.get("range") instanceof Map<?,?> range))return null;
        String id="binding:"+state.context.get("id")+":"+location.get("path")+":"+location.get("sha256")+":"+range.get("start")+":"+range.get("end");
        String methodId=null,symbol=null;
        if(variable.getEnclosingElement() instanceof ExecutableElement method){
            methodId=state.methodIdentity(owner(method),method.getKind()==ElementKind.CONSTRUCTOR?"<init>":method.getSimpleName().toString(),
                descriptor(method),declarationLocation(method));
            if(variable.getKind()==ElementKind.PARAMETER){int index=method.getParameters().indexOf(variable);if(index<0)return null;id=methodId+":parameter:"+index;}
        }
        if(variable.getKind()==ElementKind.FIELD || variable.getKind()==ElementKind.ENUM_CONSTANT) {
            var metadata=fieldMetadata(variable);
            if(variable.getKind()==ElementKind.ENUM_CONSTANT)metadata.put("kind","enum_constant");
            symbol=state.field(owner(variable),variable.getSimpleName().toString(),typeDescriptor(variable.asType()),location,metadata);
        }
        var record=map("version",1,"id",id,"name",variable.getSimpleName().toString(),"kind",variable.getKind().name(),
            "method",methodId,"symbol",symbol,"type",valueInfo(variable.asType()));
        record.putAll(location);return record;
    }
    private Map<String,Object> binding(Tree node) {
        if(node==null)return null;
        var path=TreePath.getPath(unit,node);var element=path==null?null:trees.getElement(path);
        if(!(element instanceof VariableElement variable))return null;
        if(bindingCache.containsKey(variable))return bindingCache.get(variable);
        var location=declarationLocation(variable);
        String symbol=null;
        if(variable.getKind()==ElementKind.FIELD || variable.getKind()==ElementKind.ENUM_CONSTANT) {
            var metadata=fieldMetadata(variable);
            if(variable.getKind()==ElementKind.ENUM_CONSTANT)metadata.put("kind","enum_constant");
            symbol=state.field(owner(variable),variable.getSimpleName().toString(),typeDescriptor(variable.asType()),location,metadata);
        }
        Object identity=null;
        if(location!=null && location.get("range") instanceof Map<?,?> range)
            identity="binding:"+state.context.get("id")+":"+location.get("path")+":"+location.get("sha256")+":"+range.get("start")+":"+range.get("end");
        String bindingType=null;try{bindingType=typeDescriptor(variable.asType());}catch(IllegalArgumentException ignored){}
        var result=map("id",identity,"kind",variable.getKind().name(),"symbol",symbol,"type",bindingType,"declaration",location);
        bindingCache.put(variable,result);return result;
    }
    private List<Map<String,Object>> referencedBindings(Tree node) {
        var result=new LinkedHashMap<String,Map<String,Object>>();
        new TreeScanner<Void,Void>() {
            @Override public Void scan(Tree tree,Void unused){if(tree==null || result.size()>=128)return null;return super.scan(tree,unused);}
            private void add(Tree tree){var value=binding(tree);if(value!=null && value.get("id") instanceof String id)result.putIfAbsent(id,value);}
            @Override public Void visitIdentifier(IdentifierTree tree,Void unused){add(tree);return super.visitIdentifier(tree,unused);}
            @Override public Void visitMemberSelect(MemberSelectTree tree,Void unused){add(tree);return super.visitMemberSelect(tree,unused);}
        }.scan(node,null);
        return new ArrayList<>(result.values());
    }
    private Map<String,Object> localOperation(Tree node) {
        if(errorAt(node))return null;
        if(node instanceof LiteralTree literal && literal.getValue()!=null) {
            var path=TreePath.getPath(unit,node);var type=path==null?null:trees.getTypeMirror(path);
            if(type==null || type.getKind()==TypeKind.ERROR)return null;
            String descriptor=typeDescriptor(type);
            if(!Set.of("Z","B","C","S","I","J","F","D","Ljava/lang/String;").contains(descriptor))return null;
            return map("schema_version",1,"operation","LITERAL_EVALUATION","target_type",descriptor,"target_binding",null,"target_declaration",null);
        }
        Tree target=null,value=null;
        if(node instanceof VariableTree variable){target=node;value=variable.getInitializer();}
        else if(node instanceof AssignmentTree assignment){target=assignment.getVariable();value=assignment.getExpression();}
        if(!(value instanceof LiteralTree literal) || literal.getValue()==null || localOperation(value)==null)return null;
        var proof=binding(target);
        if(proof==null || !"LOCAL_VARIABLE".equals(proof.get("kind")) || proof.get("id")==null
                || !(proof.get("type") instanceof String descriptor) || !Set.of("Z","B","C","S","I","J","F","D","Ljava/lang/String;").contains(descriptor))return null;
        return map("schema_version",1,"operation","LOCAL_LITERAL_ASSIGNMENT","target_type",proof.get("type"),"target_binding",proof.get("id"),"target_declaration",proof.get("declaration"));
    }
    public Map<String,Object> ir(Tree node) {
        if(node==null)return map("kind","empty");
        var base=map("kind","statement","label",label(node),"calls",callsIn(node));base.putAll(loc(node));
        if(node instanceof ExpressionTree) {
            base.put("value_info",valueInfo(node));
            var path=TreePath.getPath(unit,node);var type=path==null?null:trees.getTypeMirror(path);
            if(type!=null && type.getKind()!=TypeKind.ERROR && base.get("range")!=null)base.put("query_type",type.toString());
        }
        var operation=localOperation(node);if(operation!=null)base.put("local_operation",operation);
        switch(node.getKind()) {
            case IDENTIFIER,MEMBER_SELECT->{
                base.put("value_binding",valueBinding(node));
                if(node instanceof MemberSelectTree select) {
                    if(select.getIdentifier().contentEquals("class")) {
                        var tp=TreePath.getPath(unit,select.getExpression());var te=tp==null?null:trees.getElement(tp);
                        if(te instanceof TypeElement type && !errorAt(node))
                            base.put("class_literal",map("version",1,"owner",elements.getBinaryName(type).toString()));
                    } else base.put("field_receiver",ir(select.getExpression()));
                }
                var p=TreePath.getPath(unit,node);var e=p==null?null:trees.getElement(p);
                if(e instanceof TypeElement || e instanceof PackageElement)base.putAll(map("kind","reference","calls",List.of()));
                if(e instanceof VariableElement variable) {
                    base.put("binding_ref",binding(node));
                    if(variable.getConstantValue()!=null)base.put("literal",map("type",variable.asType().toString(),"value",variable.getConstantValue(),"source","COMPILER_CONSTANT"));
                    if(variable.getKind()==ElementKind.ENUM_CONSTANT)base.put("enum_constant",map("owner",owner(variable),"name",variable.getSimpleName().toString(),"symbol",((Map<?,?>)base.get("binding_ref")).get("symbol")));
                }
            }
            case STRING_LITERAL,CHAR_LITERAL,BOOLEAN_LITERAL,INT_LITERAL,LONG_LITERAL,FLOAT_LITERAL,DOUBLE_LITERAL,NULL_LITERAL->{
                base.put("literal",map("type",node.getKind().name(),"value",((LiteralTree)node).getValue(),"source","COMPILER_LITERAL"));
            }
            case METHOD_INVOCATION->{var t=(MethodInvocationTree)node;Tree receiver=t.getMethodSelect() instanceof MemberSelectTree s?s.getExpression():null;base.putAll(map("kind","call","call_site",calls.get(node),"arguments",t.getArguments().stream().map(this::ir).toList(),"receiver",ir(receiver)));}
            case NEW_CLASS->{var t=(NewClassTree)node;base.putAll(map("kind","call","call_site",calls.get(node),"arguments",t.getArguments().stream().map(this::ir).toList(),"receiver",ir(t.getEnclosingExpression())));if(t.getClassBody()!=null){var refs=referencedBindings(t.getClassBody());base.put("captured_bindings",refs);base.put("binding_references_complete",refs.size()<128);}}
            case VARIABLE->{base.putAll(map("kind","assign","value_binding",valueBinding(node),"binding",binding(node),"value",ir(((VariableTree)node).getInitializer())));}
            case ASSIGNMENT->{base.putAll(map("kind","assign","value_binding",valueBinding(((AssignmentTree)node).getVariable()),"binding",binding(((AssignmentTree)node).getVariable()),"value",ir(((AssignmentTree)node).getExpression())));}
            case LAMBDA_EXPRESSION,MEMBER_REFERENCE->{
                var refs=referencedBindings(node);
                base.putAll(map("kind","reference","calls",List.of(),"captured_bindings",refs,"binding_references_complete",refs.size()<128));
                if(node instanceof MemberReferenceTree reference)base.put("reference_receiver",ir(reference.getQualifierExpression()));
                if(node instanceof LambdaExpressionTree)base.put("query_lambda",lambdas.get(node));
            }
            case BLOCK->{base.put("kind","block");base.put("statements",((BlockTree)node).getStatements().stream().map(this::ir).toList());}
            case IF->{var t=(IfTree)node;base.putAll(map("kind","if","condition",ir(t.getCondition()),"then",ir(t.getThenStatement()),"else",ir(t.getElseStatement())));}
            case WHILE_LOOP->{var t=(WhileLoopTree)node;base.putAll(map("kind","while","condition",ir(t.getCondition()),"body",ir(t.getStatement())));}
            case DO_WHILE_LOOP->{var t=(DoWhileLoopTree)node;base.putAll(map("kind","do","condition",ir(t.getCondition()),"body",ir(t.getStatement())));}
            case FOR_LOOP->{var t=(ForLoopTree)node;base.putAll(map("kind","for","initial",map("kind","block","statements",t.getInitializer().stream().map(this::ir).toList()),"condition",t.getCondition()==null?map("kind","true"):ir(t.getCondition()),"update",map("kind","block","statements",t.getUpdate().stream().map(this::ir).toList()),"body",ir(t.getStatement())));}
            case ENHANCED_FOR_LOOP->{var t=(EnhancedForLoopTree)node;base.putAll(map("kind","foreach","iterable",ir(t.getExpression()),"body",ir(t.getStatement())));}
            case RETURN->{base.putAll(map("kind","return","value",ir(((ReturnTree)node).getExpression())));}
            case THROW->{base.putAll(map("kind","throw","value",ir(((ThrowTree)node).getExpression())));}
            case BREAK,CONTINUE->{base.put("kind",node.getKind()==Tree.Kind.BREAK?"break":"continue");}
            case TRY->{var t=(TryTree)node;base.putAll(map("kind","try","resources",t.getResources().stream().map(this::ir).toList(),"body",ir(t.getBlock()),"catches",t.getCatches().stream().map(c->map("type",c.getParameter().getType().toString(),"body",ir(c.getBlock()))).toList(),"finally",t.getFinallyBlock()==null?null:ir(t.getFinallyBlock())));}
            case PARENTHESIZED->{return ir(((ParenthesizedTree)node).getExpression());}
            case EXPRESSION_STATEMENT->{return ir(((ExpressionStatementTree)node).getExpression());}
            case CONDITIONAL_EXPRESSION->{var t=(ConditionalExpressionTree)node;base.putAll(map("kind","if","condition",ir(t.getCondition()),"then",ir(t.getTrueExpression()),"else",ir(t.getFalseExpression())));}
            case CONDITIONAL_AND,CONDITIONAL_OR->{var t=(BinaryTree)node;base.putAll(map("kind",node.getKind()==Tree.Kind.CONDITIONAL_AND?"and":"or","left",ir(t.getLeftOperand()),"right",ir(t.getRightOperand())));}
            case SWITCH,SWITCH_EXPRESSION->{base.put("kind","unsupported");base.put("reason","JAVA_SWITCH_CFG_NOT_YET_SUPPORTED");state.diagnostic("JAVA_SWITCH_CFG_NOT_YET_SUPPORTED","No guessed switch fallthrough",loc(node));}
            case LABELED_STATEMENT->{base.put("kind","unsupported");base.put("reason","LABELLED_CONTROL_FLOW");state.diagnostic("LABELLED_CONTROL_FLOW","No guessed labelled flow",loc(node));}
            default->{var refs=referencedBindings(node);base.put("referenced_bindings",refs);base.put("binding_references_complete",refs.size()<128);}
        }
        if("unsupported".equals(base.get("kind"))){var refs=referencedBindings(node);base.put("referenced_bindings",refs);base.put("binding_references_complete",refs.size()<128);}
        return base;
    }
}
