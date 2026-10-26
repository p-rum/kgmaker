"""Build trusted Maven exporter against the supplied Maven/JDK distribution offline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
p=argparse.ArgumentParser();p.add_argument('--maven-home',type=Path,required=True);p.add_argument('--java-home',type=Path,required=True)
a=p.parse_args();root=Path(__file__).resolve().parent;target=root/'maven/target';classes=target/'classes';classes.mkdir(parents=True,exist_ok=True)
def executable(name):
    for path in (a.java_home/'bin'/name, a.java_home/'bin'/(name+'.exe')):
        if path.is_file():return str(path)
    raise SystemExit('JDK executable unavailable: '+name)
cp=str(a.maven_home/'lib/*')
subprocess.run([executable('javac'),'--release','21','-proc:none','-cp',cp,'-d',str(classes),str(root/'maven/BuildExport.java')],check=True)
meta=classes/'META-INF/plexus';meta.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'maven/components.xml',meta/'components.xml')
subprocess.run([executable('jar'),'--create','--file',str(target/'kgmaker-build-export.jar'),'--date','2025-01-01T00:00:00Z','-C',str(classes),'.'],check=True)
descriptor=root/'exporters.json'
distribution=json.loads(descriptor.read_text())
distribution['exporters']['gradle']['sha256']=hashlib.sha256((root/'gradle/export.gradle').read_bytes()).hexdigest()
distribution['exporters']['maven']={'path':'maven/target/kgmaker-build-export.jar',
    'sha256':hashlib.sha256((target/'kgmaker-build-export.jar').read_bytes()).hexdigest(),
    'exporter':'maven-session-2','license':'LICENSE'}
descriptor.write_text(json.dumps(distribution,indent=2,sort_keys=True)+'\n')
print('SUCCESS: trusted Maven exporter built offline')
