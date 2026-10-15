"""Build trusted Maven exporter against the supplied Maven/JDK distribution offline."""
import argparse
from pathlib import Path
import shutil
import subprocess
p=argparse.ArgumentParser();p.add_argument('--maven-home',type=Path,required=True);p.add_argument('--java-home',type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parent;target=root/'maven/target';classes=target/'classes';classes.mkdir(parents=True,exist_ok=True)
cp=str(a.maven_home/'lib/*')
subprocess.run([str(a.java_home/'bin/javac'),'--release','21','-proc:none','-cp',cp,'-d',str(classes),str(root/'maven/BuildExport.java')],check=True)
meta=classes/'META-INF/plexus';meta.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'maven/components.xml',meta/'components.xml')
subprocess.run([str(a.java_home/'bin/jar'),'--create','--file',str(target/'kgmaker-build-export.jar'),'--date','2025-01-01T00:00:00Z','-C',str(classes),'.'],check=True)
print('SUCCESS: trusted Maven exporter built offline')
