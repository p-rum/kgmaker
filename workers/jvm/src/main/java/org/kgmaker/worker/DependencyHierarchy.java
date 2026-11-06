package org.kgmaker.worker;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import org.jetbrains.org.objectweb.asm.*;
import org.jetbrains.org.objectweb.asm.tree.*;

/** Bounded metadata-only effective classpath lookup, never class loading/initialization. */
final class DependencyHierarchy {
    static final int MAX_CLASSES=10000, MAX_ENTRIES=100000, MAX_CLASS_BYTES=16*1024*1024, MAX_TOTAL_BYTES=128*1024*1024;
    final Map<String,ClassNode> nodes=new TreeMap<>(), lookup=new TreeMap<>();
    final List<String> problems=new ArrayList<>();
    private final Set<String> selected=new HashSet<>(), unsupportedCandidates=new HashSet<>();
    private final State state;
    private int entries;
    private long bytesRead;
    DependencyHierarchy(State state) {
        this.state=state;
        for(var entry:state.classpath) {
            Path path=Path.of((String)entry.get("path"));
            var artifact=new TreeMap<String,ClassNode>();boolean enumerate=true;
            try {
                if(Files.isDirectory(path)) {
                    try(var files=Files.walk(path)) {
                        var paths=new TreeSet<Path>();var iterator=files.iterator();
                        while(iterator.hasNext()) {
                            Path file=iterator.next();if(!budget())return;
                            if(Files.isRegularFile(file)&&file.toString().endsWith(".class"))paths.add(file);
                        }
                        for(Path file:paths) {
                            String name=path.relativize(file).toString().replace(File.separatorChar,'/');
                            if(select(name,path))try(var stream=Files.newInputStream(file)){add(name,stream,path,artifact);}
                        }
                    }
                } else try(var jar=new JarFile(path.toFile(),false,JarFile.OPEN_READ,Runtime.version())) {
                    boolean multiRelease=jar.isMultiRelease();enumerate=!multiRelease;
                    if(multiRelease)problem("DEPENDENCY_HIERARCHY_MULTI_RELEASE_UNSUPPORTED",path+": effective physical lookup is supported; candidate enumeration is not");
                    var names=new TreeSet<String>();var seen=new HashSet<String>();var duplicates=new HashSet<String>();
                    var iterator=jar.entries();
                    while(iterator.hasMoreElements()) {
                        var item=iterator.nextElement();if(!budget())return;
                        String physical=item.getName();
                        if(!seen.add(physical))duplicates.add(physical);
                        String name=effectiveName(physical,multiRelease);
                        if(item.isDirectory()||name==null||name.equals("module-info.class"))continue;
                        if(!names.contains(name)&&names.size()>=MAX_CLASSES){problem("DEPENDENCY_HIERARCHY_TRUNCATED",path.toString());break;}
                        names.add(name);
                    }
                    for(String name:names) {
                        var effective=jar.getJarEntry(name);
                        if(effective==null||!select(name,path))continue;
                        String owner=name.substring(0,name.length()-6);
                        if(multiRelease)unsupportedCandidates.add(owner);
                        if(duplicates.contains(effective.getRealName())){problem("DEPENDENCY_HIERARCHY_DUPLICATE_ENTRY",path+":"+effective.getRealName());continue;}
                        try(var stream=jar.getInputStream(effective)){add(name,stream,path,artifact);}
                    }
                }
                // A truncated artifact is not a complete first-match index;
                // do not let any later entry stand in for its unknown classes.
                if(problems.contains("DEPENDENCY_HIERARCHY_TRUNCATED"))return;
                lookup.putAll(artifact);if(enumerate)nodes.putAll(artifact);
            } catch(IOException|IllegalArgumentException error) {
                problem("DEPENDENCY_HIERARCHY_UNAVAILABLE",path+": "+error.getMessage());return;
            }
        }
    }
    private String effectiveName(String name,boolean multiRelease) {
        if(!name.endsWith(".class"))return null;
        if(!name.startsWith("META-INF/"))return name;
        String prefix="META-INF/versions/";
        if(!multiRelease||!name.startsWith(prefix))return null;
        int slash=name.indexOf('/',prefix.length());if(slash<0)return null;
        try {
            int version=Integer.parseInt(name.substring(prefix.length(),slash));
            return version>=9&&version<=Runtime.version().feature()?name.substring(slash+1):null;
        }catch(NumberFormatException ignored){return null;}
    }
    private boolean budget() {
        if(++entries>MAX_ENTRIES||selected.size()>=MAX_CLASSES) {
            problem("DEPENDENCY_HIERARCHY_TRUNCATED","Selected classpath exceeds bounded hierarchy index");return false;
        }
        return true;
    }
    private boolean select(String resource,Path path) {
        if(resource.equals("module-info.class"))return false;
        String owner=resource.substring(0,resource.length()-6);
        if(state.platformResource(owner)!=null){problem("DEPENDENCY_HIERARCHY_PLATFORM_SHADOWED",owner+" ignored in selected classpath "+path);return false;}
        if(selected.size()>=MAX_CLASSES){problem("DEPENDENCY_HIERARCHY_TRUNCATED",path.toString());return false;}
        if(!selected.add(owner)){problem("DEPENDENCY_HIERARCHY_SHADOWED",owner+" ignored in later classpath entry "+path);return false;}
        return true;
    }
    private void add(String resource,InputStream stream,Path path,Map<String,ClassNode> artifact) throws IOException {
        String owner=resource.substring(0,resource.length()-6);
        try {
            long remaining=MAX_TOTAL_BYTES-bytesRead;
            if(remaining<=0){problem("DEPENDENCY_HIERARCHY_TRUNCATED","Aggregate class-byte budget exhausted");return;}
            byte[] data=stream.readNBytes((int)Math.min(MAX_CLASS_BYTES+1L,remaining+1));
            if(data.length>remaining){bytesRead=MAX_TOTAL_BYTES;problem("DEPENDENCY_HIERARCHY_TRUNCATED","Aggregate class-byte budget exhausted");return;}
            bytesRead+=data.length;
            if(data.length>MAX_CLASS_BYTES){problem("DEPENDENCY_HIERARCHY_TRUNCATED",path+":"+resource);return;}
            var node=new ClassNode();new ClassReader(data).accept(node,ClassReader.SKIP_CODE|ClassReader.SKIP_DEBUG|ClassReader.SKIP_FRAMES);
            if(!owner.equals(node.name)){problem("DEPENDENCY_HIERARCHY_INVALID_CLASS",path+":"+resource);return;}
            artifact.put(owner,node);
        } catch(IllegalArgumentException|IndexOutOfBoundsException error) {
            problem("DEPENDENCY_HIERARCHY_INVALID_CLASS",path+":"+resource+": "+error.getMessage());
        }
    }
    boolean selected(String owner){return selected.contains(owner);}
    boolean candidateUnsupported(String owner){return unsupportedCandidates.contains(owner);}
    private void problem(String code,String detail){if(!problems.contains(code)){problems.add(code);state.diagnostic(code,detail,null);}}
}
