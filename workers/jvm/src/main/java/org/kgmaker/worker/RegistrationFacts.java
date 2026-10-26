package org.kgmaker.worker;

import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.lang.model.element.*;
import javax.lang.model.type.*;
import javax.lang.model.util.*;
import java.util.*;
import static org.kgmaker.worker.State.map;

/** Exact compiler declarations only; no registry, factory or project code runs. */
final class RegistrationFacts {
    private static final String FACTORY="org.springframework.beans.factory.FactoryBean";
    private static final String REGISTRAR="org.springframework.context.annotation.ImportBeanDefinitionRegistrar";
    private static final String REGISTRY="org.springframework.beans.factory.support.BeanDefinitionRegistry";
    private final Trees trees; private final Types types; private final Elements elements;
    RegistrationFacts(Trees trees,Types types,Elements elements){this.trees=trees;this.types=types;this.elements=elements;}
    private String name(TypeMirror type){
        var e=types.asElement(types.erasure(type));
        return e instanceof TypeElement t?elements.getBinaryName(t).toString():null;
    }
    private TypeMirror ancestor(TypeMirror type,String wanted){
        var pending=new ArrayDeque<TypeMirror>();pending.add(type);var seen=new HashSet<String>();
        while(!pending.isEmpty() && seen.size()<128){
            var item=pending.removeFirst();if(item.getKind()==TypeKind.ERROR)continue;
            if(!seen.add(item.toString()))continue;
            if(wanted.equals(name(item)))return item;
            pending.addAll(types.directSupertypes(item));
        }
        return null;
    }
    private boolean callable(ExecutableElement method,String wanted,int count){
        return method.getSimpleName().contentEquals(wanted)&&method.getParameters().size()==count
            &&method.getModifiers().contains(Modifier.PUBLIC)&&!method.getModifiers().contains(Modifier.STATIC);
    }
    private List<ExecutableElement> methods(TypeElement type,String wanted,int count){
        return elements.getAllMembers(type).stream().filter(e->e instanceof ExecutableElement)
            .map(e->(ExecutableElement)e).filter(e->callable(e,wanted,count)).toList();
    }
    private String owner(List<ExecutableElement> methods){
        return methods.size()==1?elements.getBinaryName((TypeElement)methods.getFirst().getEnclosingElement()).toString():null;
    }
    Map<String,Object> factory(TypeMirror type){
        if(type.getKind()!=TypeKind.DECLARED)return null;
        var match=ancestor(type,FACTORY);
        if(match==null)return null;
        String product=null;
        if(match instanceof DeclaredType declared && declared.getTypeArguments().size()==1){
            var argument=declared.getTypeArguments().getFirst();
            if(argument.getKind()==TypeKind.DECLARED)product=name(argument);
        }
        var element=types.asElement(types.erasure(type));
        var object=element instanceof TypeElement t?owner(methods(t,"getObject",0)):null;
        var objectType=element instanceof TypeElement t?owner(methods(t,"getObjectType",0)):null;
        return map("schema_version",1,"product_type",product,"get_object_owner",object,"get_type_owner",objectType);
    }
    Map<String,Object> describe(TypeElement type){
        var result=new LinkedHashMap<String,Object>();var factory=factory(type.asType());
        if(factory!=null)result.put("factory_bean",factory);
        if(ancestor(type.asType(),REGISTRAR)!=null){
            var candidates=methods(type,"registerBeanDefinitions",2).stream().filter(this::registrarMethod).toList();
            boolean custom=methods(type,"registerBeanDefinitions",3).stream().anyMatch(e->!REGISTRAR.equals(name(e.getEnclosingElement().asType())));
            result.put("bean_registrar",map("schema_version",1,"method_owner",owner(candidates),"custom_name_generator",custom));
        }
        return result;
    }
    private boolean registrarMethod(ExecutableElement method){
        return callable(method,"registerBeanDefinitions",2)
            &&"org.springframework.core.type.AnnotationMetadata".equals(name(method.getParameters().get(0).asType()))
            &&REGISTRY.equals(name(method.getParameters().get(1).asType()))
            &&method.getReturnType().getKind()==TypeKind.VOID;
    }
    private String literalClass(TreePath path,ExpressionTree expression){
        if(!(expression instanceof MemberSelectTree select)||!select.getIdentifier().contentEquals("class"))return null;
        var element=trees.getElement(new TreePath(new TreePath(path,expression),select.getExpression()));
        return element instanceof TypeElement type?elements.getBinaryName(type).toString():null;
    }
    Map<String,Object> method(ExecutableElement method,MethodTree tree,TreePath path,boolean erroneous){
        var result=new LinkedHashMap<String,Object>();
        if(!(method.getEnclosingElement() instanceof TypeElement type))return result;
        var factory=factory(method.getReturnType());
        if(factory!=null)result.put("factory_bean_return",factory);
        var body=tree.getBody();
        if(registrarMethod(method)&&ancestor(type.asType(),REGISTRAR)!=null){
            var values=new ArrayList<Map<String,Object>>();String reason="COMPLEX_REGISTRAR_BODY";
            boolean valid=!erroneous&&body!=null&&body.getStatements().size()<=128;
            if(valid)for(var statement:body.getStatements()){
                if(!(statement instanceof ExpressionStatementTree expr)||!(expr.getExpression() instanceof MethodInvocationTree call)
                        ||!(call.getMethodSelect() instanceof MemberSelectTree select)||call.getArguments().size()!=2){valid=false;break;}
                var callPath=TreePath.getPath(path.getCompilationUnit(),call);
                var receiver=trees.getElement(TreePath.getPath(path.getCompilationUnit(),select.getExpression()));
                var target=trees.getElement(callPath);
                if(!method.getParameters().get(1).equals(receiver)||!(target instanceof ExecutableElement executable)
                        ||!executable.getSimpleName().contentEquals("registerBeanDefinition")
                        ||!REGISTRY.equals(name(executable.getEnclosingElement().asType()))
                        ||!(call.getArguments().get(0) instanceof LiteralTree literal)||!(literal.getValue() instanceof String bean)
                        ||bean.isBlank()||bean.length()>512||bean.startsWith("&")
                        ||!(call.getArguments().get(1) instanceof NewClassTree created)||created.getClassBody()!=null||created.getArguments().size()!=1){valid=false;break;}
                var constructor=trees.getElement(TreePath.getPath(path.getCompilationUnit(),created));
                String product=literalClass(TreePath.getPath(path.getCompilationUnit(),created.getArguments().getFirst()).getParentPath(),created.getArguments().getFirst());
                if(!(constructor instanceof ExecutableElement c)||!"org.springframework.beans.factory.support.RootBeanDefinition".equals(name(c.getEnclosingElement().asType()))||product==null){valid=false;break;}
                values.add(map("name",bean,"type",product));
            }
            if(body!=null&&body.getStatements().size()>128)reason="REGISTRATION_LIMIT_EXCEEDED";
            result.put("bean_registrations",map("schema_version",1,"status",valid?"LITERAL":"UNSUPPORTED","values",valid?values:List.of(),"reason",erroneous?"COMPILER_ERROR":valid?"LITERAL_REGISTRY_CALLS":reason));
        }
        if(ancestor(type.asType(),FACTORY)!=null&&(callable(method,"getObject",0)||callable(method,"getObjectType",0))){
            boolean object=method.getSimpleName().contentEquals("getObject");String product=null;
            if(!erroneous&&body!=null&&body.getStatements().size()==1&&body.getStatements().getFirst() instanceof ReturnTree returned){
                var expression=returned.getExpression();
                if(object&&expression instanceof NewClassTree created&&created.getClassBody()==null&&created.getArguments().isEmpty()){
                    var constructor=trees.getElement(TreePath.getPath(path.getCompilationUnit(),created));
                    if(constructor instanceof ExecutableElement c)product=name(c.getEnclosingElement().asType());
                }else if(!object&&expression!=null)product=literalClass(TreePath.getPath(path.getCompilationUnit(),expression).getParentPath(),expression);
            }
            result.put("factory_return",map("schema_version",1,"kind",object?"OBJECT":"TYPE","status",product==null?"UNSUPPORTED":"LITERAL","type",product,"reason",erroneous?"COMPILER_ERROR":product==null?"CUSTOM_FACTORY_BODY":"SINGLE_LITERAL_FACTORY_RETURN"));
        }
        return result;
    }
}
