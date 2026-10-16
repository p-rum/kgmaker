package org.kgmaker.build;
import org.apache.maven.eventspy.EventSpy;
import org.apache.maven.execution.ExecutionEvent;
import org.apache.maven.project.MavenProject;
import org.apache.maven.artifact.Artifact;
import org.apache.maven.model.Dependency;
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
  static String effective(MavenProject p,String value) {if(value==null)return null;String result=value;for(String name:p.getProperties().stringPropertyNames())result=result.replace("${"+name+"}",p.getProperties().getProperty(name));result=result.replace("${project.groupId}",p.getGroupId()).replace("${project.artifactId}",p.getArtifactId()).replace("${project.version}",p.getVersion());return result;}
  static Map<String,Object> dependency(MavenProject p,Dependency d) {Map<String,Object> v=new LinkedHashMap<>();v.put("group_id",effective(p,d.getGroupId()));v.put("artifact_id",effective(p,d.getArtifactId()));v.put("version",effective(p,d.getVersion()));v.put("scope",effective(p,d.getScope()));v.put("type",effective(p,d.getType()));v.put("classifier",effective(p,d.getClassifier()));v.put("optional",d.isOptional());return v;}
  static Map<String,Object> artifact(Artifact a) {Map<String,Object> v=new LinkedHashMap<>();v.put("group_id",a.getGroupId());v.put("artifact_id",a.getArtifactId());v.put("version",a.getVersion());v.put("scope",a.getScope());v.put("type",a.getType());v.put("classifier",a.getClassifier());v.put("file",a.getFile()==null?null:a.getFile().getAbsolutePath());return v;}
  static List<String> profiles(MavenProject p) {Set<String> ids=new TreeSet<>();p.getActiveProfiles().forEach(x->ids.add(x.getId()));p.getInjectedProfileIds().values().forEach(ids::addAll);return new ArrayList<>(ids);}
  static List<Map<String,Object>> importedBoms(MavenProject p) {List<Map<String,Object>> values=new ArrayList<>();for(MavenProject current=p;current!=null;current=current.getParent())if(current.getOriginalModel().getDependencyManagement()!=null)for(Dependency d:current.getOriginalModel().getDependencyManagement().getDependencies())if("import".equals(d.getScope())&&"pom".equals(d.getType()))values.add(dependency(current,d));values.sort(Comparator.comparing(Object::toString));return values;}
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
    List<String> relative=new ArrayList<>(), generated=new ArrayList<>(), files=new ArrayList<>();
    for(String raw:new LinkedHashSet<>(roots)){Path path=Path.of(raw);if(!path.isAbsolute())path=p.getBasedir().toPath().resolve(path);path=path.normalize();if(!path.startsWith(root))continue;String rel=root.relativize(path).toString().replace('\\','/');relative.add(rel);if(rel.contains("/target/generated-")||rel.startsWith("target/generated-"))generated.add(rel);if(Files.isDirectory(path))try(var stream=Files.walk(path)){stream.filter(Files::isRegularFile).filter(f->f.toString().endsWith(".java")||f.toString().endsWith(".kt")).forEach(f->files.add(root.relativize(f).toString().replace('\\','/')));}}
    Collections.sort(files);
    List<Map<String,Object>> effective=new ArrayList<>();for(Artifact a:p.getArtifacts())effective.add(artifact(a));effective.sort(Comparator.comparing(Object::toString));
    List<Map<String,Object>> managed=new ArrayList<>();if(p.getDependencyManagement()!=null)for(Dependency d:p.getDependencyManagement().getDependencies())managed.add(dependency(p,d));
    List<Map<String,Object>> boms=importedBoms(p);
    Map<String,Object> c=new LinkedHashMap<>();c.put("id",id);c.put("module",module);c.put("source_set",sourceSet);c.put("scope",test?"test":"production");c.put("source_roots",relative);c.put("generated_source_roots",generated);c.put("source_files",files);c.put("classpath_paths",test?p.getTestClasspathElements():p.getCompileClasspathElements());c.put("output_paths",List.of(test?p.getBuild().getTestOutputDirectory():p.getBuild().getOutputDirectory()));c.put("build_system","maven");c.put("build_profiles",profiles(p));c.put("effective_dependencies",effective);c.put("dependency_management",managed);c.put("imported_boms",boms);
    if(p.getParent()!=null)c.put("parent",Map.of("group_id",p.getParent().getGroupId(),"artifact_id",p.getParent().getArtifactId(),"version",p.getParent().getVersion()));
    String release=p.getProperties().getProperty("maven.compiler.release",p.getProperties().getProperty("java.version"));c.put("compiler_options",release==null?Map.of():Map.of("release",release));Map<String,Object> toolchain=new LinkedHashMap<>();toolchain.put("java_version",System.getProperty("java.version"));toolchain.put("java_home",System.getProperty("java.home"));toolchain.put("java_vendor",System.getProperty("java.vendor"));toolchain.put("maven_version",System.getProperty("maven.version","3.9.x"));c.put("toolchain",toolchain);contexts.put(id,c);
  }
  public void onEvent(Object event) throws Exception {
    if(!(event instanceof ExecutionEvent))return;ExecutionEvent e=(ExecutionEvent)event;
    if(e.getType()==ExecutionEvent.Type.ProjectSucceeded){modules.put(e.getProject().getId(),"SUCCESS");capture(e.getProject(),false);capture(e.getProject(),true);}
    if(e.getType()==ExecutionEvent.Type.ProjectFailed)modules.put(e.getProject().getId(),"FAILED");
    if(e.getType()==ExecutionEvent.Type.ProjectSkipped)modules.put(e.getProject().getId(),"SKIPPED");
    if(e.getType()==ExecutionEvent.Type.SessionEnded){Path out=Path.of(System.getProperty("kgmaker.export.path"));Files.writeString(out,json(Map.of("schema_version",1,"exporter","maven-session-2","contexts",contexts.values(),"modules",modules,"diagnostics",List.of())));}
  }
}
