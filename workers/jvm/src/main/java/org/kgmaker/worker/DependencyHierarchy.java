package org.kgmaker.worker;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import org.jetbrains.org.objectweb.asm.*;
import org.jetbrains.org.objectweb.asm.tree.*;

/** Metadata-only, ordered selected-classpath index. Never defines or initializes a class. */
final class DependencyHierarchy {
    static final int MAX_CLASSES=10000, MAX_ENTRIES=100000, MAX_CLASS_BYTES=16*1024*1024, MAX_TOTAL_BYTES=128*1024*1024;
    final Map<String,ClassNode> nodes=new TreeMap<>();
    final List<String> problems=new ArrayList<>();
    private final Set<String> selected=new HashSet<>();
    private final State state;
    private int entries;
    private long bytesRead;
    DependencyHierarchy(State state) {
        this.state=state;
        for(var entry:state.classpath) {
            Path path=Path.of((String)entry.get("path"));
            try {
                if(Files.isDirectory(path)) {
                    try(var files=Files.walk(path)) {
                        var paths=new TreeSet<Path>();
                        var iterator=files.iterator();
                        while(iterator.hasNext()) {
                            Path file=iterator.next();if(!budget())return;
                            if(Files.isRegularFile(file)&&file.toString().endsWith(".class"))paths.add(file);
                        }
                        for(Path file:paths) {
                            String name=path.relativize(file).toString().replace(File.separatorChar,'/');
                            if(select(name,path))try(var stream=Files.newInputStream(file)){add(name,stream,path);}
                        }
                    }
                } else try(var jar=new JarFile(path.toFile())) {
                    // Bound enumeration before sorting, including irrelevant archive entries.
                    boolean multiRelease=jar.isMultiRelease();
                    if(multiRelease)problem("DEPENDENCY_HIERARCHY_MULTI_RELEASE_UNSUPPORTED",path.toString());
                    var names=new TreeMap<String,JarEntry>();var ambiguous=new HashSet<String>();
                    var iterator=jar.entries();
                    while(iterator.hasMoreElements()) {
                        var item=iterator.nextElement();if(!budget())return;
                        String name=item.getName();
                        if(item.isDirectory()||!name.endsWith(".class"))continue;
                        if(multiRelease && name.matches("META-INF/versions/[0-9]+/.+"))name=name.replaceFirst("META-INF/versions/[0-9]+/", "");
                        else if(name.startsWith("META-INF/"))continue;
                        if(names.size()>=MAX_CLASSES){problem("DEPENDENCY_HIERARCHY_TRUNCATED",path.toString());break;}
                        if(names.putIfAbsent(name,item)!=null)ambiguous.add(name);
                    }
                    for(var item:names.entrySet())if(select(item.getKey(),path)) {
                        if(multiRelease)continue;
                        if(ambiguous.contains(item.getKey())){problem("DEPENDENCY_HIERARCHY_DUPLICATE_ENTRY",path+":"+item.getKey());continue;}
                        try(var stream=jar.getInputStream(item.getValue())){add(item.getKey(),stream,path);}
                    }
                }
            } catch(IOException|IllegalArgumentException error) {
                problem("DEPENDENCY_HIERARCHY_UNAVAILABLE",path+": "+error.getMessage());
                return;
            }
        }
    }
    private boolean budget() {
        if(++entries>MAX_ENTRIES||selected.size()>=MAX_CLASSES) {
            problem("DEPENDENCY_HIERARCHY_TRUNCATED","Selected classpath exceeds bounded hierarchy index");return false;
        }
        return true;
    }
    private boolean select(String resource,Path path) {
        String owner=resource.substring(0,resource.length()-6);
        if(selected.size()>=MAX_CLASSES){problem("DEPENDENCY_HIERARCHY_TRUNCATED",path.toString());return false;}
        if(!selected.add(owner)){problem("DEPENDENCY_HIERARCHY_SHADOWED",owner+" ignored in later classpath entry "+path);return false;}
        return true;
    }
    private void add(String resource,InputStream stream,Path path) throws IOException {
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
            nodes.put(owner,node);
        } catch(IllegalArgumentException|IndexOutOfBoundsException error) {
            problem("DEPENDENCY_HIERARCHY_INVALID_CLASS",path+":"+resource+": "+error.getMessage());
        }
    }
    boolean selected(String owner){return selected.contains(owner);}
    private void problem(String code,String detail){if(!problems.contains(code)){problems.add(code);state.diagnostic(code,detail,null);}}
}
