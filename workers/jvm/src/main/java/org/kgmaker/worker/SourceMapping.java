package org.kgmaker.worker;

import org.jetbrains.org.objectweb.asm.*;
import org.jetbrains.org.objectweb.asm.tree.*;
import java.util.*;
import static org.kgmaker.worker.State.map;

/** Declaration mapping only: generated instructions never become source call expressions. */
final class SourceMapping {
    private final State state;
    private final Map<String,ClassNode> application;
    private final Set<String> ambiguousOwners;
    private String abiFailure;
    SourceMapping(State state,Map<String,ClassNode> application,Set<String> ambiguousOwners) {
        this.state=state;this.application=application;this.ambiguousOwners=ambiguousOwners;
    }

    private boolean sameRealm(Map<String,Object> left,Map<String,Object> right) {
        for(String key:List.of("repo_id","module","source_set","scope")) {
            Object value=left.get(key);
            if(!(value instanceof String) || ((String)value).isEmpty() || !value.equals(right.get(key)))return false;
        }
        return true;
    }
    private Map<String,Object> source(String owner,String name,String descriptor,boolean expectedStatic) {
        // Source declarations belong to the selected request context. Scope is
        // not encoded in State.methodIdentity, so identity equality alone fails open.
        if(ambiguousOwners.contains(owner.replace('.','/')) || !sameRealm(state.realm(owner.replace('/','.'),null),state.context))return null;
        var value=state.symbols.get(state.methodIdentity(owner.replace('/','.'),name,descriptor,null));
        if(value==null || value.get("path")==null || value.get("range")==null)return null;
        if(!(value.get("jvm_static") instanceof Boolean actualStatic)) {
            abiFailure="SOURCE_METHOD_ABI_UNAVAILABLE";return null;
        }
        if(actualStatic!=expectedStatic){abiFailure="SOURCE_METHOD_ABI_MISMATCH";return null;}
        return value;
    }
    private boolean metadata(ClassNode owner,int kind) {
        for(var annotations:List.of(owner.visibleAnnotations==null?List.<AnnotationNode>of():owner.visibleAnnotations,
                                   owner.invisibleAnnotations==null?List.<AnnotationNode>of():owner.invisibleAnnotations))
            for(var annotation:annotations)if(annotation.desc.equals("Lkotlin/Metadata;") && annotation.values!=null)
                for(int i=0;i+1<annotation.values.size();i+=2)
                    if(annotation.values.get(i).equals("k") && Integer.valueOf(kind).equals(annotation.values.get(i+1)))return true;
        return false;
    }
    private Map<String,Object> defaultImpl(ClassNode owner,MethodNode method) {
        if((method.access&Opcodes.ACC_STATIC)==0 || !metadata(owner,3))return null;
        // InnerClasses is compiler structure, not a guessed '$DefaultImpls' suffix.
        var outers=new TreeSet<String>();
        for(var inner:owner.innerClasses)if(owner.name.equals(inner.name) && "DefaultImpls".equals(inner.innerName)
                && inner.outerName!=null)outers.add(inner.outerName);
        if(outers.size()!=1)return null;
        String outer=outers.first();var contract=application.get(outer);
        // A helper from another artifact realm cannot claim this checkout's body.
        if(!sameRealm(state.realm(owner.name.replace('/','.'),null),
                      state.realm(outer.replace('/','.'),null)))return null;
        if(contract==null || (contract.access&Opcodes.ACC_INTERFACE)==0 || !metadata(contract,1))return null;
        Type[] args=Type.getArgumentTypes(method.desc);
        if(args.length==0 || !args[0].equals(Type.getObjectType(outer)))return null;
        String descriptor=Type.getMethodDescriptor(Type.getReturnType(method.desc),Arrays.copyOfRange(args,1,args.length));
        if(contract.methods.stream().noneMatch(m->m.name.equals(method.name)&&m.desc.equals(descriptor)
                && (m.access&(Opcodes.ACC_STATIC|Opcodes.ACC_PRIVATE))==0))return null;
        var result=source(outer,method.name,descriptor,false);
        return result!=null && result.get("path").toString().endsWith(".kt")?result:null;
    }
    private Map<String,Object> bridge(ClassNode owner,MethodNode method) {
        if((method.access&(Opcodes.ACC_BRIDGE|Opcodes.ACC_SYNTHETIC))!=(Opcodes.ACC_BRIDGE|Opcodes.ACC_SYNTHETIC)
                || !method.tryCatchBlocks.isEmpty())return null;
        MethodInsnNode delegate=null;boolean returned=false;
        for(var instruction:method.instructions) {
            int opcode=instruction.getOpcode();if(opcode<0)continue;
            if(returned)return null;
            if(instruction instanceof MethodInsnNode invoke) {
                if(delegate!=null || !invoke.owner.equals(owner.name) || !invoke.name.equals(method.name)
                        || invoke.desc.equals(method.desc) || invoke.getOpcode()==Opcodes.INVOKESTATIC)return null;
                delegate=invoke;
            }else if(opcode>=Opcodes.IRETURN && opcode<=Opcodes.RETURN) {
                if(delegate==null)return null;returned=true;
            }else if(!(instruction instanceof VarInsnNode && opcode>=Opcodes.ILOAD && opcode<=Opcodes.ALOAD)
                    && !(instruction instanceof TypeInsnNode && opcode==Opcodes.CHECKCAST))return null;
        }
        if(delegate==null || !returned)return null;
        final MethodInsnNode selected=delegate;
        if(owner.methods.stream().noneMatch(m->m.name.equals(selected.name)&&m.desc.equals(selected.desc)
                && (m.access&(Opcodes.ACC_BRIDGE|Opcodes.ACC_SYNTHETIC|Opcodes.ACC_ABSTRACT|Opcodes.ACC_STATIC))==0))return null;
        return source(delegate.owner,delegate.name,delegate.desc,false);
    }
    Map<String,Object> mapMethod(ClassNode owner,MethodNode method,String bytecodeId) {
        abiFailure=null;
        boolean ambiguous=ambiguousOwners.contains(owner.name);
        Map<String,Object> target=null;String reason=ambiguous?"AMBIGUOUS_BYTECODE_CLASS":"NO_SOURCE_MAPPING";
        if(!ambiguous && (method.access&(Opcodes.ACC_BRIDGE|Opcodes.ACC_SYNTHETIC))==0) {
            target=source(owner.name,method.name,method.desc,(method.access&Opcodes.ACC_STATIC)!=0);
            if(target!=null)reason="OWNER_NAME_DESCRIPTOR_MATCH";
        }
        if(!ambiguous && target==null && (method.access&Opcodes.ACC_BRIDGE)!=0) {
            target=bridge(owner,method);if(target!=null)reason="VERIFIED_BRIDGE_DELEGATE";
        }
        if(!ambiguous && target==null) { target=defaultImpl(owner,method);if(target!=null)reason="KOTLIN_DEFAULT_IMPLS_SIGNATURE"; }
        if(target==null) {
            if(!ambiguous && abiFailure!=null)reason=abiFailure;
            state.diagnostics.add(map("code","BYTECODE_ONLY_SOURCE_MAPPING","message","No compiler-proven source declaration mapping for "+owner.name+"."+method.name+method.desc,
                "bytecode_method_id",bytecodeId,"reason",reason,"context_id",state.context.get("id")));
            return map("source_mapping_ids",List.of(),"source_mapping_reason",reason,"source_mapping_path",null,"source_mapping_range",null);
        }
        state.facts.add(map("kind","maps_to_source","source",bytecodeId,"target",target.get("id"),
            "evidence_kind","SYMBOL_RESOLVED","resolution_reason",reason,"context_id",state.context.get("id"),
            "path",target.get("path"),"range",target.get("range"),"sha256",target.get("sha256"),
            "artifact_hashes",state.context.get("bytecode_artifacts"),"representation","DECLARATION_MAPPING"));
        return map("source_mapping_ids",List.of(target.get("id")),"source_mapping_reason",reason,
                   "source_mapping_path",target.get("path"),"source_mapping_range",target.get("range"));
    }
}
