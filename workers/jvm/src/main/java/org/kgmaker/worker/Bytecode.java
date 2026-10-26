package org.kgmaker.worker;

import org.jetbrains.org.objectweb.asm.*;
import org.jetbrains.org.objectweb.asm.tree.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.JarFile;
import static org.kgmaker.worker.State.map;

/** Pinned Kotlin-2.1.10 bundled ASM reader + classpath method lookup/CHA.
 * Instruction indexes are explicitly NOT labelled bytecode offsets.
 */
public final class Bytecode implements AutoCloseable {
    private final State state;
    private final ClassLoader loader=ClassLoader.getPlatformClassLoader();
    private final DependencyHierarchy hierarchy;
    private final Map<String,ClassNode> classes=new HashMap<>();
    private final Map<String,ClassNode> application=new TreeMap<>();
    private final Set<String> missingTypes=new HashSet<>();
    private final Set<String> sourceHierarchyUnavailable=new HashSet<>();
    private final Map<String,Map<String,Object>> dispatchCache=new HashMap<>();
    public final List<Map<String,Object>> cfgs=new ArrayList<>();
    public Bytecode(State state) throws Exception {
        this.state=state;
        hierarchy=new DependencyHierarchy(state);
        classes.putAll(hierarchy.nodes);
    }
    private ClassNode read(String owner) {
        if(classes.containsKey(owner))return classes.get(owner);
        if(hierarchy.selected(owner)){classes.put(owner,null);return null;}
        try(var stream=loader.getResourceAsStream(owner+".class")) {
            if(stream==null){classes.put(owner,null);return null;}
            var node=new ClassNode();new ClassReader(stream.readAllBytes()).accept(node,ClassReader.SKIP_CODE|ClassReader.SKIP_DEBUG|ClassReader.SKIP_FRAMES);
            classes.put(owner,node);return node;
        }catch(IOException|IllegalArgumentException error){state.diagnostic("BYTECODE_CLASS_UNAVAILABLE",owner+": "+error.getMessage(),null);classes.put(owner,null);return null;}
    }
    /** Class-file membership check only; never loads/initializes project code. */
    public boolean hasDeclaredMethod(String owner,String name,String descriptor) {
        var node=read(owner.replace('.','/'));
        return node!=null && node.methods.stream().anyMatch(method->method.name.equals(name)&&method.desc.equals(descriptor));
    }
    private String classMethod(String owner,String name,String descriptor,Set<String> visited) {
        if(visited.size()>=256){hierarchyDepth();return null;}
        if(!visited.add(owner))return null;
        var c=read(owner);if(c==null)return null;
        if(c.methods.stream().anyMatch(m->m.name.equals(name)&&m.desc.equals(descriptor)))return owner;
        if(name.equals("<init>"))return null;
        return c.superName==null?null:classMethod(c.superName,name,descriptor,visited);
    }
    private String definingOwner(String owner,String name,String descriptor,Set<String> visited) {
        String direct=classMethod(owner,name,descriptor,new HashSet<>());
        if(direct!=null)return direct;
        if(name.equals("<init>"))return null;
        var inherited=new LinkedHashSet<String>();
        for(String cursor=owner;cursor!=null && visited.add(cursor);) {
            var c=read(cursor);if(c==null)break;
            for(String parent:c.interfaces)interfaceMethods(parent,name,descriptor,new HashSet<>(),inherited);
            cursor=c.superName;
        }
        var mostSpecific=new ArrayList<String>();
        for(String candidate:inherited)if(inherited.stream().noneMatch(other->!other.equals(candidate)&&subtype(other,candidate,new HashSet<>())))mostSpecific.add(candidate);
        if(mostSpecific.size()>1)state.diagnostic("AMBIGUOUS_INTERFACE_METHOD_LOOKUP",owner+"."+name+descriptor,null);
        return mostSpecific.size()==1?mostSpecific.get(0):null;
    }
    private void interfaceMethods(String owner,String name,String descriptor,Set<String> visited,Set<String> result) {
        if(visited.size()>=256){hierarchyDepth();return;}
        if(!visited.add(owner))return;
        var c=read(owner);if(c==null)return;
        if(c.methods.stream().anyMatch(m->m.name.equals(name)&&m.desc.equals(descriptor)&&(m.access&(Opcodes.ACC_STATIC|Opcodes.ACC_PRIVATE))==0))result.add(owner);
        for(String parent:c.interfaces)interfaceMethods(parent,name,descriptor,visited,result);
    }
    private String definingField(String owner,String name,String descriptor,Set<String> visited) {
        if(visited.size()>=256){hierarchyDepth();return null;}
        if(!visited.add(owner))return null;
        var c=read(owner);if(c==null)return null;
        if(c.fields.stream().anyMatch(f->f.name.equals(name)&&f.desc.equals(descriptor)))return owner;
        for(String parent:c.interfaces){String found=definingField(parent,name,descriptor,visited);if(found!=null)return found;}
        return c.superName==null?null:definingField(c.superName,name,descriptor,visited);
    }
    private boolean subtype(String child,String parent,Set<String> visited) {
        if(child.equals(parent))return true;
        if(visited.size()>=256){hierarchyDepth();return false;}
        if(!visited.add(child))return false;
        var c=read(child);if(c==null)return false;
        if(c.superName!=null&&subtype(c.superName,parent,visited))return true;
        return c.interfaces.stream().anyMatch(p->subtype(p,parent,visited));
    }
    @SuppressWarnings("unchecked")
    public void analyze(List<?> roots) throws Exception {
        // A source backend without a type-hierarchy proof must not reuse stale
        // selected output hierarchy for the same owner.
        var sourceOwners=new TreeSet<String>();var attributedTypes=new HashSet<String>();
        for(var symbol:state.symbols.values())if(symbol.get("path")!=null && symbol.get("owner") instanceof String owner) {
            sourceOwners.add(owner.replace('.','/'));
            if(symbol.containsKey("jvm_interfaces"))attributedTypes.add(owner.replace('.','/'));
        }
        for(String owner:sourceOwners)if(hierarchy.selected(owner)&&!attributedTypes.contains(owner)) {
            hierarchy.nodes.remove(owner);sourceHierarchyUnavailable.add(owner);
            state.diagnostic("SOURCE_HIERARCHY_UNAVAILABLE",owner+": compiled copy cannot replace compiler source hierarchy",null);
            if(!hierarchy.problems.contains("SOURCE_HIERARCHY_UNAVAILABLE"))hierarchy.problems.add("SOURCE_HIERARCHY_UNAVAILABLE");
        }
        // Compiler-attributed source types own their identities even when a
        // selected output/JAR also contains an older class with the same name.
        for(var symbol:new ArrayList<>(state.symbols.values()))if(symbol.get("path")!=null && symbol.containsKey("jvm_interfaces")) {
            var node=new ClassNode();node.name=((String)symbol.get("owner")).replace('.','/');
            node.superName=(String)symbol.get("jvm_superclass");node.interfaces=new ArrayList<>((List<String>)symbol.get("jvm_interfaces"));
            node.access=sourceFlags(symbol);
            if("interface".equals(symbol.get("kind")))node.access|=Opcodes.ACC_INTERFACE|Opcodes.ACC_ABSTRACT;
            for(var method:state.symbols.values())if(method.get("path")!=null && symbol.get("owner").equals(method.get("owner")) && method.get("descriptor") instanceof String descriptor && descriptor.startsWith("("))
                node.methods.add(new MethodNode(sourceFlags(method),(String)method.get("name"),descriptor,null,null));
            classes.put(node.name,node);
            hierarchy.nodes.put(node.name,node);
        }
        for(Object item:roots) {
            Path path=Path.of(item instanceof String?(String)item:(String)((Map<?,?>)item).get("path"));
            Map<String,Object> realm=item instanceof Map<?,?> && ((Map<?,?>)item).get("realm") instanceof Map<?,?>?
                (Map<String,Object>)((Map<?,?>)item).get("realm"):state.context;
            if(Files.isDirectory(path))try(var paths=Files.walk(path)) {
                for(Path file:paths.filter(p->p.toString().endsWith(".class")).sorted().toList())load(Files.readAllBytes(file),realm);
            }else if(path.toString().endsWith(".jar"))try(var jar=new JarFile(path.toFile())) {
                for(var entry:jar.stream().filter(e->e.getName().endsWith(".class")&&!e.getName().startsWith("META-INF/versions/")).sorted(Comparator.comparing(java.util.jar.JarEntry::getName)).toList())
                    try(var stream=jar.getInputStream(entry)){load(stream.readAllBytes(),realm);}
            }else state.diagnostic("UNSUPPORTED_BYTECODE_ROOT",path.toString(),null);
        }
        for(var entry:application.entrySet())for(MethodNode method:entry.getValue().methods)inspect(entry.getValue(),method);
        for(var site:state.sites)if(site.get("dispatch_receiver") instanceof String receiver &&
            Set.of("VIRTUAL","INTERFACE").contains(site.get("dispatch_kind"))) {
            var symbol=state.symbols.get(site.get("declared_target"));
            if(symbol!=null)dispatch(site,receiver,(String)symbol.get("name"),(String)symbol.get("descriptor"));
        }
    }
    private void load(byte[] data,Map<String,Object> realm) {
        if(application.size()>=10000)throw new IllegalStateException("bytecode class limit exceeded");
        var c=new ClassNode();new ClassReader(data).accept(c,ClassReader.SKIP_FRAMES);
        if(application.putIfAbsent(c.name,c)!=null){state.diagnostic("DUPLICATE_BYTECODE_CLASS",c.name,null);return;}
        if(!hierarchy.selected(c.name)){classes.put(c.name,c);state.bindRealm(c.name.replace('/','.'),realm);}
    }
    private String method(ClassNode owner,MethodNode method) {
        String canonical=state.method(owner.name.replace('/','.'),method.name,method.desc,null,
            map("modifiers",flags(method.access),"annotations",annotations(method.visibleAnnotations,method.invisibleAnnotations)));
        String identity="bytecode:"+canonical;
        var value=new LinkedHashMap<>(state.symbols.get(canonical));value.putAll(map("id",identity,"kind","bytecode_method",
            "source_mapping_ids",state.symbols.get(canonical).get("path")!=null?List.of(canonical):List.of(),
            "source_mapping_reason",state.symbols.get(canonical).get("path")!=null?"OWNER_NAME_DESCRIPTOR_MATCH":"NO_SOURCE_MAPPING",
            "synthetic",(method.access&Opcodes.ACC_SYNTHETIC)!=0,"bridge",(method.access&Opcodes.ACC_BRIDGE)!=0,"origin","generated"));
        state.symbols.put(identity,value);return identity;
    }
    private String target(String owner,String name,String descriptor) {
        String definition=definingOwner(owner,name,descriptor,new HashSet<>());
        return definition==null?null:authoritativeMethod(definition,name,descriptor);
    }
    @SuppressWarnings("unchecked")
    private void inspect(ClassNode owner,MethodNode method) {
        String caller=method(owner,method);
        var instructions=method.instructions.toArray();
        Map<AbstractInsnNode,Integer> positions=new IdentityHashMap<>();
        for(int i=0;i<instructions.length;i++)positions.put(instructions[i],i);
        int line=-1;
        for(int i=0;i<instructions.length;i++) {
            var instruction=instructions[i];
            if(instruction instanceof LineNumberNode number)line=number.line;
            if(instruction instanceof MethodInsnNode invoke) {
                String resolved=target(invoke.owner,invoke.name,invoke.desc);
                String identity="bytecode-call:"+caller+":"+i;
                var site=map("id",identity,"caller",caller,"declared_target",resolved,"invocation_kind",opcode(invoke.getOpcode()),
                    "receiver_type",invoke.owner.replace('/','.'),"dispatch_candidates",new ArrayList<String>(),"dispatch_complete",false,
                    "resolution_reason",resolved!=null?"JVM_METHOD_LOOKUP":"MISSING_CLASS_OR_METHOD","evidence_kind",resolved!=null?"SYMBOL_RESOLVED":"UNRESOLVED",
                    "context_id",state.context.get("id"),"bytecode_offset",null,"instruction_index",i,"source_line",line<0?null:line,
                    "source_file_attribute",owner.sourceFile,"path",null,"range",null,"origin","generated");
                if(invoke.getOpcode()==Opcodes.INVOKEVIRTUAL||invoke.getOpcode()==Opcodes.INVOKEINTERFACE) {
                    dispatch(site,invoke.owner,invoke.name,invoke.desc);
                }
                state.sites.add(site);
                if(resolved==null)state.diagnostic("BYTECODE_UNRESOLVED_TARGET",invoke.owner+"."+invoke.name+invoke.desc,null);
            }else if(instruction instanceof InvokeDynamicInsnNode dynamic) {
                String reason=dynamic.bsm.getOwner().equals("java/lang/invoke/LambdaMetafactory")?"LAMBDA_REFERENCE_CREATION":"UNKNOWN_INVOKEDYNAMIC_BOOTSTRAP";
                var candidates=new ArrayList<String>();
                if(reason.equals("LAMBDA_REFERENCE_CREATION"))for(Object arg:dynamic.bsmArgs)if(arg instanceof Handle handle){String symbol=target(handle.getOwner(),handle.getName(),handle.getDesc());if(symbol!=null)candidates.add(symbol);}
                state.sites.add(map("id","bytecode-call:"+caller+":"+i,"caller",caller,"declared_target",null,"dispatch_candidates",candidates,
                    "dispatch_complete",false,"invocation_kind","INVOKEDYNAMIC","resolution_reason",reason,"evidence_kind","UNRESOLVED",
                    "context_id",state.context.get("id"),"bytecode_offset",null,"instruction_index",i,"path",null,"range",null,"origin","generated"));
                state.diagnostic(reason,"Reference creation is not execution of the implementation",null);
            }else if(instruction instanceof FieldInsnNode field) {
                String definition=definingField(field.owner,field.name,field.desc,new HashSet<>());
                String id=state.field((definition==null?field.owner:definition).replace('/','.'),field.name,field.desc,null,null);
                if(definition==null)state.diagnostic("BYTECODE_FIELD_UNRESOLVED",field.owner+"."+field.name+field.desc,null);
                state.facts.add(map("kind",field.getOpcode()==Opcodes.PUTFIELD||field.getOpcode()==Opcodes.PUTSTATIC?"writes_field":"reads_field",
                    "source",caller,"target",id,"evidence_kind",definition==null?"SYNTAX_CANDIDATE":"SYMBOL_RESOLVED","context_id",state.context.get("id"),"path",null,"range",null,"instruction_index",i));
            }
        }
        if(instructions.length>0)cfgs.add(cfg(caller,method,positions));
    }
    private int sourceFlags(Map<String,Object> symbol) {
        int flags=0;
        if(symbol.get("modifiers") instanceof List<?> modifiers)for(Object modifier:modifiers)flags|=switch(modifier.toString()) {
            case "public"->Opcodes.ACC_PUBLIC;case "protected"->Opcodes.ACC_PROTECTED;case "private"->Opcodes.ACC_PRIVATE;
            case "static"->Opcodes.ACC_STATIC;case "final"->Opcodes.ACC_FINAL;case "abstract"->Opcodes.ACC_ABSTRACT;default->0;};
        return flags;
    }
    private String authoritativeMethod(String owner,String name,String descriptor) {
        for(var symbol:state.symbols.values())if(symbol.get("path")!=null && !"bytecode_method".equals(symbol.get("kind")) && owner.replace('/','.').equals(symbol.get("owner")) &&
            name.equals(symbol.get("name")) && descriptor.equals(symbol.get("descriptor")))return (String)symbol.get("id");
        return state.method(owner.replace('/','.'),name,descriptor,null,null);
    }
    private void hierarchyDepth() {
        if(!hierarchy.problems.contains("DEPENDENCY_HIERARCHY_DEPTH_LIMIT")) {
            hierarchy.problems.add("DEPENDENCY_HIERARCHY_DEPTH_LIMIT");
            state.diagnostic("DEPENDENCY_HIERARCHY_DEPTH_LIMIT","Hierarchy lookup exceeded 256 visited types",null);
        }
    }
    private boolean completeHierarchy(String owner,Set<String> visited) {
        if(sourceHierarchyUnavailable.contains(owner))return false;
        if(visited.size()>=256){hierarchyDepth();return false;}
        if(!visited.add(owner))return true;
        var node=read(owner);
        if(node==null){if(missingTypes.add(owner))state.diagnostic("DEPENDENCY_HIERARCHY_MISSING_TYPE",owner,null);return false;}
        boolean complete=node.superName==null||completeHierarchy(node.superName,visited);
        for(String parent:node.interfaces)complete=completeHierarchy(parent,visited)&&complete;
        return complete;
    }
    private void dispatch(Map<String,Object> site,String receiver,String name,String descriptor) {
        String key=receiver+"."+name+descriptor;
        if(dispatchCache.containsKey(key)){site.putAll(dispatchCache.get(key));return;}
        var candidates=new TreeSet<String>();
        String declaration=definingOwner(receiver,name,descriptor,new HashSet<>());
        var declarationClass=declaration==null?null:read(declaration);
        var declarationMethod=declarationClass==null?null:declarationClass.methods.stream().filter(m->m.name.equals(name)&&m.desc.equals(descriptor)).findFirst().orElse(null);
        if(declarationClass!=null && declarationMethod!=null &&
            ((declarationClass.access&Opcodes.ACC_FINAL)!=0 || (declarationMethod.access&(Opcodes.ACC_FINAL|Opcodes.ACC_STATIC|Opcodes.ACC_PRIVATE))!=0))return;
        if(declarationMethod!=null && (declarationMethod.access&(Opcodes.ACC_PUBLIC|Opcodes.ACC_PROTECTED))==0) {
            state.diagnostic("DEPENDENCY_DISPATCH_ACCESS_UNSUPPORTED",declaration+"."+name+descriptor,null);
            site.put("dispatch_algorithm","CHA_ORDERED_SELECTED_CLASSPATH");
            site.put("dispatch_completeness_reason","PACKAGE_PRIVATE_OVERRIDE_ACCESS_UNSUPPORTED;OPEN_WORLD_RUNTIME_TYPES");
            site.put("dispatch_classpath",state.classpath);return;
        }
        var available=new TreeMap<String,ClassNode>(hierarchy.nodes);application.forEach(available::putIfAbsent);
        boolean missing=!completeHierarchy(receiver,new HashSet<>());
        for(var candidate:available.values())if(!completeHierarchy(candidate.name,new HashSet<>()))missing=true;
        for(var candidate:available.values())if(!hierarchy.problems.contains("DEPENDENCY_HIERARCHY_TRUNCATED") && !hierarchy.problems.contains("DEPENDENCY_HIERARCHY_UNAVAILABLE") && (candidate.access&(Opcodes.ACC_INTERFACE|Opcodes.ACC_ABSTRACT))==0 &&
            subtype(candidate.name,receiver,new HashSet<>())) {
            if(!completeHierarchy(candidate.name,new HashSet<>())){missing=true;continue;}
            String definition=definingOwner(candidate.name,name,descriptor,new HashSet<>());
            var owner=definition==null?null:read(definition);
            if(owner==null)continue;
            var implementation=owner.methods.stream().filter(m->m.name.equals(name)&&m.desc.equals(descriptor)).findFirst().orElse(null);
            if(implementation==null||(implementation.access&(Opcodes.ACC_STATIC|Opcodes.ACC_PRIVATE|Opcodes.ACC_ABSTRACT))!=0)continue;
            // Package-private overriding across package boundaries needs additional access proof.
            if((implementation.access&(Opcodes.ACC_PUBLIC|Opcodes.ACC_PROTECTED))==0) {
                state.diagnostic("DEPENDENCY_DISPATCH_ACCESS_UNSUPPORTED",definition+"."+name+descriptor,null);continue;
            }
            candidates.add(authoritativeMethod(definition,name,descriptor));
        }
        var result=new LinkedHashMap<String,Object>();
        result.put("dispatch_candidates",new ArrayList<>(candidates));
        result.put("dispatch_algorithm","CHA_ORDERED_SELECTED_CLASSPATH");result.put("dispatch_complete",false);
        var reasons=new ArrayList<>(hierarchy.problems);if(missing)reasons.add("MISSING_HIERARCHY_TYPE");reasons.add("OPEN_WORLD_RUNTIME_TYPES");
        result.put("dispatch_completeness_reason",String.join(";",reasons));
        result.put("dispatch_classpath",state.classpath);
        dispatchCache.put(key,result);site.putAll(result);
    }
    private Map<String,Object> cfg(String caller,MethodNode method,Map<AbstractInsnNode,Integer> positions) {
        var blocks=new ArrayList<Map<String,Object>>();var edges=new ArrayList<Map<String,Object>>();
        String entry=caller+":entry",exit=caller+":exit",exception=caller+":exceptional-exit";
        blocks.add(map("id",entry,"kind","entry","label","entry"));blocks.add(map("id",exit,"kind","exit","label","exit"));blocks.add(map("id",exception,"kind","exceptional_exit","label","uncaught exception"));
        var insns=method.instructions.toArray();var executable=new TreeMap<Integer,String>();
        for(int i=0;i<insns.length;i++)if(insns[i].getOpcode()>=0){String id=caller+":instruction:"+i;executable.put(i,id);blocks.add(map("id",id,"kind","basic_block","label",opcode(insns[i].getOpcode()),"instruction_index",i,"source_range",null));}
        if(!executable.isEmpty())edges.add(map("source",entry,"target",executable.firstEntry().getValue(),"kind","normal"));
        for(var item:executable.entrySet()) {
            int i=item.getKey(),op=insns[i].getOpcode();String current=item.getValue();
            var next=executable.higherEntry(i);
            if(op>=Opcodes.IRETURN&&op<=Opcodes.RETURN)edges.add(map("source",current,"target",exit,"kind","return"));
            else if(op==Opcodes.ATHROW)edges.add(map("source",current,"target",exception,"kind","throw"));
            else if(insns[i] instanceof JumpInsnNode jump) {
                var target=executable.ceilingEntry(positions.get(jump.label));
                if(target!=null)edges.add(map("source",current,"target",target.getValue(),"kind",op==Opcodes.GOTO?"normal":"true","loop_back",target.getKey()<=i));
                if(op!=Opcodes.GOTO&&next!=null)edges.add(map("source",current,"target",next.getValue(),"kind","false"));
            }else if(insns[i] instanceof TableSwitchInsnNode sw) {
                switchEdges(edges,current,sw.labels,sw.dflt,positions,executable);
            }else if(insns[i] instanceof LookupSwitchInsnNode sw) {
                switchEdges(edges,current,sw.labels,sw.dflt,positions,executable);
            }else if(next!=null)edges.add(map("source",current,"target",next.getValue(),"kind","normal"));
            else edges.add(map("source",current,"target",exit,"kind","normal"));
            for(var handler:method.tryCatchBlocks)if(i>=positions.get(handler.start)&&i<positions.get(handler.end)) {
                var destination=executable.ceilingEntry(positions.get(handler.handler));
                if(destination!=null)edges.add(map("source",current,"target",destination.getValue(),"kind","exception","condition",handler.type==null?"finally/any exception":handler.type.replace('/','.')));
            }
        }
        return map("method",caller,"entry",entry,"exit",exit,"exceptional_exit",exception,"blocks",blocks,"edges",edges,
            "representation","BYTECODE","context_id",state.context.get("id"),"status","PARTIAL","limitations",List.of("Instruction indexes are not bytecode offsets.","Exceptional edges are conservative, not path feasibility."));
    }
    private void switchEdges(List<Map<String,Object>> edges,String source,List<LabelNode> labels,LabelNode defaultLabel,Map<AbstractInsnNode,Integer> positions,TreeMap<Integer,String> executable) {
        for(int n=0;n<labels.size();n++){var dest=executable.ceilingEntry(positions.get(labels.get(n)));if(dest!=null)edges.add(map("source",source,"target",dest.getValue(),"kind","case","condition","case index "+n));}
        var dest=executable.ceilingEntry(positions.get(defaultLabel));if(dest!=null)edges.add(map("source",source,"target",dest.getValue(),"kind","case","condition","default"));
    }
    private List<String> flags(int flags){var list=new ArrayList<String>();if((flags&Opcodes.ACC_STATIC)!=0)list.add("static");if((flags&Opcodes.ACC_PRIVATE)!=0)list.add("private");if((flags&Opcodes.ACC_PUBLIC)!=0)list.add("public");return list;}
    @SafeVarargs private final List<Map<String,Object>> annotations(List<AnnotationNode>... sets) {
        var result=new ArrayList<Map<String,Object>>();for(var set:sets)if(set!=null)for(var annotation:set){var values=new LinkedHashMap<String,Object>();if(annotation.values!=null)for(int i=0;i<annotation.values.size();i+=2)values.put((String)annotation.values.get(i),annotationValue(annotation.values.get(i+1)));result.add(map("name",Type.getType(annotation.desc).getClassName(),"values",values));}return result;
    }
    private Object annotationValue(Object v){if(v instanceof Type t)return t.getClassName();if(v instanceof String[] a)return Type.getType(a[0]).getClassName()+"."+a[1];if(v instanceof List<?> l)return l.stream().map(this::annotationValue).toList();if(v instanceof AnnotationNode a)return annotations(List.of(a)).getFirst();return v;}
    private String opcode(int op){return switch(op){case Opcodes.INVOKEVIRTUAL->"VIRTUAL";case Opcodes.INVOKEINTERFACE->"INTERFACE";case Opcodes.INVOKESTATIC->"STATIC";case Opcodes.INVOKESPECIAL->"SPECIAL";case Opcodes.GOTO->"GOTO";case Opcodes.IFEQ->"IFEQ";case Opcodes.ATHROW->"ATHROW";default->"opcode "+op;};}
    @Override public void close() {}
}
