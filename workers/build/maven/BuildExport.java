package org.kgmaker.build;
import org.apache.maven.eventspy.EventSpy;
import org.apache.maven.execution.ExecutionEvent;
import org.apache.maven.project.MavenProject;
import org.apache.maven.model.Plugin;
import org.codehaus.plexus.util.xml.Xpp3Dom;
import java.nio.file.*;
import java.util.*;
/** Maven 3.9.9 effective session export. No model inferred from XML strings. */
public final class BuildExport implements EventSpy {
  private final Map<String,Object> contexts=new LinkedHashMap<>();
  private final Map<String,Object> modules=new LinkedHashMap<>();
  public void init(Context context) {}
  public void close() {}
  static String quote(String s) {StringBuilder b=new StringBuilder("\""); for(char c:s.toCharArray()) {switch(c){case '"': b.append("\\\"");break;case '\\':b.append("\\\\");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default: if(c<32)b.append(String.format("\\u%04x",(int)c));else b.append(c);}}return b.append('"').toString();}
  static String json(Object v) {if(v==null)return "null";if(v instanceof String)return quote((String)v);if(v instanceof Number||v instanceof Boolean)return v.toString();if(v instanceof Map){List<String>a=new ArrayList<>();((Map<?,?>)v).forEach((k,x)->a.add(quote(k.toString())+":"+json(x)));return "{"+String.join(",",a)+"}";}if(v instanceof Collection){List<String>a=new ArrayList<>();for(Object x:(Collection<?>)v)a.add(json(x));return "["+String.join(",",a)+"]";}throw new IllegalArgumentException(v.toString());}
  void capture(MavenProject p, boolean test) throws Exception {
    Path root=Path.of(System.getProperty("kgmaker.snapshot.root")).toAbsolutePath().normalize();
    String module=root.relativize(p.getBasedir().toPath().toAbsolutePath().normalize()).toString().replace('\\','/');if(module.isEmpty())module="root";
    String sourceSet=test?"test":"main";String id=module+":"+sourceSet;
    List<String> roots=new ArrayList<>(test?p.getTestCompileSourceRoots():p.getCompileSourceRoots());
    for(Plugin plugin:p.getBuildPlugins()) if(plugin.getArtifactId().equals("kotlin-maven-plugin")) {
      List<Xpp3Dom> configs=new ArrayList<>();if(plugin.getConfiguration() instanceof Xpp3Dom)configs.add((Xpp3Dom)plugin.getConfiguration());
      for(var execution:plugin.getExecutions())if(execution.getGoals().contains(test?"test-compile":"compile")&&execution.getConfiguration() instanceof Xpp3Dom)configs.add((Xpp3Dom)execution.getConfiguration());
      for(Xpp3Dom config:configs){Xpp3Dom dirs=config.getChild("sourceDirs");if(dirs!=null)for(Xpp3Dom dir:dirs.getChildren()){String value=dir.getValue();if(value!=null&&!value.contains("${"))roots.add(value);}}
    }
    List<String> relative=new ArrayList<>(), files=new ArrayList<>();
    for(String raw:new LinkedHashSet<>(roots)){Path path=Path.of(raw);if(!path.isAbsolute())path=p.getBasedir().toPath().resolve(path);path=path.normalize();if(!path.startsWith(root))continue;relative.add(root.relativize(path).toString().replace('\\','/'));if(Files.isDirectory(path))try(var stream=Files.walk(path)){stream.filter(Files::isRegularFile).filter(f->f.toString().endsWith(".java")||f.toString().endsWith(".kt")).forEach(f->files.add(root.relativize(f).toString().replace('\\','/')));}}
    Collections.sort(files);
    Map<String,Object> c=new LinkedHashMap<>();c.put("id",id);c.put("module",module);c.put("source_set",sourceSet);c.put("scope",test?"test":"production");c.put("source_roots",relative);c.put("source_files",files);c.put("classpath_paths",test?p.getTestClasspathElements():p.getCompileClasspathElements());c.put("output_paths",List.of(test?p.getBuild().getTestOutputDirectory():p.getBuild().getOutputDirectory()));c.put("build_system","maven");c.put("build_profiles",p.getActiveProfiles().stream().map(x->x.getId()).toList());
    String release=p.getProperties().getProperty("maven.compiler.release",p.getProperties().getProperty("java.version"));c.put("compiler_options",release==null?Map.of():Map.of("release",release));c.put("toolchain",Map.of("java_version",System.getProperty("java.version"),"maven_version",System.getProperty("maven.version","3.9.x")));contexts.put(id,c);
  }
  public void onEvent(Object event) throws Exception {
    if(!(event instanceof ExecutionEvent))return;ExecutionEvent e=(ExecutionEvent)event;
    if(e.getType()==ExecutionEvent.Type.ProjectSucceeded){modules.put(e.getProject().getId(),"SUCCESS");capture(e.getProject(),false);capture(e.getProject(),true);}
    if(e.getType()==ExecutionEvent.Type.ProjectFailed)modules.put(e.getProject().getId(),"FAILED");
    if(e.getType()==ExecutionEvent.Type.ProjectSkipped)modules.put(e.getProject().getId(),"SKIPPED");
    if(e.getType()==ExecutionEvent.Type.SessionEnded){Path out=Path.of(System.getProperty("kgmaker.export.path"));Files.writeString(out,json(Map.of("schema_version",1,"exporter","maven-session-1","contexts",contexts.values(),"modules",modules,"diagnostics",List.of())));}
  }
}
