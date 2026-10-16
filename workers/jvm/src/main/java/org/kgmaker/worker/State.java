package org.kgmaker.worker;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.jar.JarFile;

public final class State {
    public final Map<String,Object> request, context;
    public final Path root;
    public final Map<String,Map<String,Object>> symbols = new TreeMap<>();
    public final List<Map<String,Object>> sites = new ArrayList<>(), bodies = new ArrayList<>(), facts = new ArrayList<>(), diagnostics = new ArrayList<>();
    public final List<Map<String,Object>> classpath = new ArrayList<>();
    public final Map<Path,String> inputs = new LinkedHashMap<>();
    private final Map<String,Map<String,Object>> realms = new HashMap<>();

    @SuppressWarnings("unchecked")
    public State(Map<String,Object> request) throws IOException {
        this.request=request;
        root=Path.of((String)request.get("root")).toRealPath();
        context=(Map<String,Object>)request.get("context");
        if(context==null || !(context.get("id") instanceof String)) throw new IllegalArgumentException("context.id required");
        for(Object item:(List<?>)request.getOrDefault("classpath",List.of())) {
            Map<String,Object> entry=item instanceof String ? map("path",item) : new LinkedHashMap<>((Map<String,Object>)item);
            Path p=Path.of((String)entry.get("path")).toRealPath(); entry.put("path",p.toString());
            classpath.add(entry);
        }
    }
    public static Map<String,Object> map(Object... values) {
        var result=new LinkedHashMap<String,Object>();
        for(int i=0;i<values.length;i+=2) result.put((String)values[i],values[i+1]);
        return result;
    }
    public static String hash(byte[] content) {
        try {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));}
        catch(Exception e){throw new IllegalStateException(e);}
    }
    public static String fileHash(Path path) throws IOException {
        try {
            var digest=MessageDigest.getInstance("SHA-256");
            try(var stream=Files.newInputStream(path)){byte[] buffer=new byte[65536];int n;while((n=stream.read(buffer))>=0)digest.update(buffer,0,n);}
            return HexFormat.of().formatHex(digest.digest());
        }catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException(e);}
    }
    private String artifactHash(Path path){try{return fileHash(path);}catch(IOException e){throw new UncheckedIOException(e);}}
    public void bindRealm(String owner,Map<String,Object> realm){realms.put(owner,realm);}
    public String text(Path file) throws IOException {
        byte[] raw=Files.readAllBytes(file); inputs.put(file.toRealPath(),hash(raw));
        return new String(raw,StandardCharsets.UTF_8);
    }
    public Map<String,Object> location(Path file,long start,long end,int startLine,int startColumn,int endLine,int endColumn) {
        String relative=root.relativize(file.toAbsolutePath().normalize()).toString().replace('\\','/');
        if(relative.startsWith("../")) throw new IllegalArgumentException("Source outside root");
        String origin="handwritten";
        for(Object raw:(List<?>)context.getOrDefault("generated_source_roots",List.of())) {
            String generated=(String)raw;
            if(relative.equals(generated)||relative.startsWith(generated.replaceAll("/+$","")+"/")){origin="generated";break;}
        }
        return map("path",relative,"sha256",inputs.get(file.toAbsolutePath().normalize()),"origin",origin,
            "range",start<0||end<0?null:map("start",start,"end",end,"start_line",startLine,"start_column",startColumn,"end_line",endLine,"end_column",endColumn));
    }
    @SuppressWarnings("unchecked")
    public Map<String,Object> realm(String owner,Map<String,Object> loc) {
        if(loc!=null && loc.get("path")!=null) return context;
        if(realms.containsKey(owner)) return realms.get(owner);
        String resource=owner.replace('.','/')+".class";
        for(Map<String,Object> entry:classpath) {
            Path p=Path.of((String)entry.get("path"));
            boolean found=Files.isDirectory(p)&&Files.isRegularFile(p.resolve(resource));
            if(!found&&p.toString().endsWith(".jar")) try(var jar=new JarFile(p.toFile())){found=jar.getJarEntry(resource)!=null;}catch(IOException ignored){}
            if(found) {
                Map<String,Object> value=entry.get("realm") instanceof Map<?,?>? (Map<String,Object>)entry.get("realm"):
                    map("repo_id","dependency","module",entry.containsKey("sha256")?entry.get("sha256"):artifactHash(Files.isDirectory(p)?p.resolve(resource):p),"source_set","classpath","scope",context.get("scope"));
                realms.put(owner,value); return value;
            }
        }
        var jdk=map("repo_id","toolchain","module","jdk-"+System.getProperty("java.version"),"source_set","platform","scope",context.get("scope"));
        realms.put(owner,jdk); return jdk;
    }
    public String prefix(Map<String,Object> realm) {
        return "jvm:"+realm.get("repo_id")+":"+realm.get("module")+":"+realm.get("source_set")+":"+context.get("id");
    }
    public String method(String owner,String name,String descriptor,Map<String,Object> loc,Map<String,Object> metadata) {
        var realm=realm(owner,loc);
        String identity=prefix(realm)+":method:"+owner+"."+name+descriptor;
        var value=map("id",identity,"owner",owner,"name",name,"descriptor",descriptor,"kind",name.equals("<init>")?"constructor":"method",
            "scope",realm.get("scope"),"context_id",context.get("id"),"origin",loc==null?"dependency":"handwritten","path",null,"range",null);
        if(loc!=null)value.putAll(loc); if(metadata!=null)value.putAll(metadata);
        if(loc!=null || !symbols.containsKey(identity)) symbols.put(identity,value);
        if(symbols.size()>20000) throw new IllegalStateException("symbol output limit exceeded");
        return identity;
    }
    public String type(String owner,Map<String,Object> loc,Map<String,Object> metadata) {
        var realm=realm(owner,loc); String identity=prefix(realm)+":type:"+owner;
        var value=map("id",identity,"owner",owner,"name",owner.substring(owner.lastIndexOf('.')+1),"kind","class",
            "scope",realm.get("scope"),"context_id",context.get("id"),"origin",loc==null?"dependency":"handwritten","path",null,"range",null);
        if(loc!=null)value.putAll(loc);if(metadata!=null)value.putAll(metadata);
        if(loc!=null || !symbols.containsKey(identity))symbols.put(identity,value);
        return identity;
    }
    public String field(String owner,String name,String descriptor,Map<String,Object> loc,Map<String,Object> metadata) {
        var realm=realm(owner,loc); String identity=prefix(realm)+":field:"+owner+"."+name+":"+descriptor;
        var value=map("id",identity,"owner",owner,"name",name,"descriptor",descriptor,"kind","field",
            "scope",realm.get("scope"),"context_id",context.get("id"),"origin",loc==null?"dependency":"handwritten","path",null,"range",null);
        if(loc!=null)value.putAll(loc);if(metadata!=null)value.putAll(metadata);
        if(loc!=null||!symbols.containsKey(identity))symbols.put(identity,value);
        return identity;
    }
    @SuppressWarnings("unchecked")
    public String site(String caller,Map<String,Object> loc,String target,String invocation,String receiver,String reason) {
        if(sites.size()>50000)throw new IllegalStateException("call output limit exceeded");
        var range=(Map<String,Object>)loc.get("range");
        String identity="call:"+caller+":"+loc.get("sha256")+":"+(range==null?"unknown":range.get("start")+":"+range.get("end"));
        var value=map("id",identity,"caller",caller,"declared_target",target,"invocation_kind",invocation,
            "receiver_type",receiver,"dispatch_candidates",new ArrayList<>(),"dispatch_complete",false,
            "resolution_reason",reason,"evidence_kind",target==null?"UNRESOLVED":"SYMBOL_RESOLVED","context_id",context.get("id"));
        value.putAll(loc); sites.add(value);return identity;
    }
    public void diagnostic(String code,String reason,Map<String,Object> loc) {
        var value=map("code",code,"reason",reason);if(loc!=null)value.putAll(loc);diagnostics.add(value);
    }
    public void verifyInputs() throws IOException {
        for(var item:inputs.entrySet())if(!hash(Files.readAllBytes(item.getKey())).equals(item.getValue()))
            throw new IllegalStateException("MIXED_SNAPSHOT:"+root.relativize(item.getKey()));
    }
}
