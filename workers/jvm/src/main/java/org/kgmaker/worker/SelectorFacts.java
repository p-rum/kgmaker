package org.kgmaker.worker;

import com.sun.source.tree.*;
import javax.lang.model.element.*;
import javax.lang.model.type.*;
import javax.lang.model.util.*;
import java.util.*;
import static org.kgmaker.worker.State.map;

/** Bounded compiler declaration facts, never selector execution or class loading. */
final class SelectorFacts {
    static final String SELECTOR="org.springframework.context.annotation.ImportSelector";
    static final String DEFERRED="org.springframework.context.annotation.DeferredImportSelector";
    static final String REGISTRAR="org.springframework.context.annotation.ImportBeanDefinitionRegistrar";
    private static final int LIMIT=128;
    private final Types types;
    private final Elements elements;
    private final Map<String,Map<String,Object>> cached=new HashMap<>();
    SelectorFacts(Types types,Elements elements){this.types=types;this.elements=elements;}

    private String name(TypeMirror type) {
        var element=types.asElement(types.erasure(type));
        return element instanceof TypeElement owner?elements.getBinaryName(owner).toString():null;
    }
    private boolean selectMethod(ExecutableElement method) {
        return method.getSimpleName().contentEquals("selectImports")
            && method.getParameters().size()==1
            && "org.springframework.core.type.AnnotationMetadata".equals(name(method.getParameters().getFirst().asType()))
            && method.getReturnType() instanceof ArrayType array
            && "java.lang.String".equals(name(array.getComponentType()))
            && method.getModifiers().contains(Modifier.PUBLIC)
            && !method.getModifiers().contains(Modifier.STATIC);
    }
    @SuppressWarnings("unchecked")
    Map<String,Object> describe(TypeElement owner) {
        String identity=elements.getBinaryName(owner).toString();
        if(cached.containsKey(identity))return cached.get(identity);
        var names=new LinkedHashSet<String>();
        var queue=new ArrayDeque<TypeMirror>(types.directSupertypes(owner.asType()));
        boolean complete=true;
        while(!queue.isEmpty()) {
            if(names.size()>=LIMIT){complete=false;break;}
            var current=queue.removeFirst();
            if(current.getKind()==TypeKind.ERROR){complete=false;continue;}
            String value=name(current);
            if(value==null){complete=false;continue;}
            if(names.add(value))queue.addAll(types.directSupertypes(current));
        }
        var result=map("type_hierarchy",map("schema_version",1,"complete",complete,"types",List.copyOf(names)));
        String kind=names.contains(DEFERRED)?"DEFERRED_IMPORT_SELECTOR":names.contains(SELECTOR)?"IMPORT_SELECTOR":names.contains(REGISTRAR)?"REGISTRAR":null;
        if(kind!=null) {
            var methods=elements.getAllMembers(owner).stream().filter(e->e instanceof ExecutableElement)
                .map(e->(ExecutableElement)e).toList();
            var candidates=methods.stream().filter(this::selectMethod).toList();
            String methodOwner=candidates.size()==1?elements.getBinaryName((TypeElement)candidates.getFirst().getEnclosingElement()).toString():null;
            boolean filter=methods.stream().anyMatch(e->e.getSimpleName().contentEquals("getExclusionFilter") && e.getParameters().isEmpty()
                && !((TypeElement)e.getEnclosingElement()).getQualifiedName().contentEquals(SELECTOR));
            boolean group=methods.stream().anyMatch(e->e.getSimpleName().contentEquals("getImportGroup") && e.getParameters().isEmpty()
                && !((TypeElement)e.getEnclosingElement()).getQualifiedName().contentEquals(DEFERRED));
            result.put("import_selector",map("schema_version",1,"kind",kind,"method_owner",methodOwner,"custom_filter",filter,"custom_group",group));
        }
        cached.put(identity,result);return result;
    }
    Map<String,Object> literalReturn(ExecutableElement method,MethodTree tree,boolean erroneous) {
        if(!selectMethod(method) || !(method.getEnclosingElement() instanceof TypeElement owner)
                || !describe(owner).containsKey("import_selector"))return null;
        String reason="NON_LITERAL_OR_COMPLEX_BODY";
        if(!erroneous && tree.getBody()!=null && tree.getBody().getStatements().size()==1
                && tree.getBody().getStatements().getFirst() instanceof ReturnTree returned
                && returned.getExpression() instanceof NewArrayTree array && array.getInitializers()!=null) {
            if(array.getInitializers().size()>LIMIT)reason="TARGET_LIMIT_EXCEEDED";
            else {
                var values=new ArrayList<String>();
                for(var item:array.getInitializers()) {
                    if(!(item instanceof LiteralTree literal) || !(literal.getValue() instanceof String value)
                            || value.length()>512 || !value.matches("[A-Za-z_$][\\w$]*(?:\\.[A-Za-z_$][\\w$]*)+")) {
                        return map("schema_version",1,"status","UNSUPPORTED","values",List.of(),"reason","NON_CLASS_NAME_LITERAL");
                    }
                    values.add(value);
                }
                return map("schema_version",1,"status","LITERAL","values",values,"reason","SINGLE_LITERAL_STRING_ARRAY_RETURN");
            }
        }
        return map("schema_version",1,"status","UNSUPPORTED","values",List.of(),"reason",erroneous?"COMPILER_ERROR":reason);
    }
}
