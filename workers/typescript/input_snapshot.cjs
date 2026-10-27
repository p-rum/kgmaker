'use strict';
// Filesystem observations only. TypeScript itself still parses and resolves.
const fs = require('node:fs');
const path = require('node:path');
const LIMIT = 20000;
const ENTRY_LIMIT = 100000;
const order = (a,b) => Buffer.compare(Buffer.from(a),Buffer.from(b));

function inputSnapshot(ts, root, readInput) {
  const observations = new Map(), directories = new Map();
  let entryCount = 0;
  const absolute = value => path.resolve(value);
  const metadata = value => {
    const relative=path.relative(path.join(root,'.kgmaker'),absolute(value));
    return relative==='' || (relative!=='..' && !relative.startsWith('..'+path.sep) && !path.isAbsolute(relative));
  };
  const normalize = value => absolute(value).split(path.sep).join('/');
  function remember(op,file,value) {
    file=absolute(file);
    if(metadata(file)) return value;
    const key=op+'\0'+file, record={op,path:normalize(file),value};
    if(observations.has(key) && JSON.stringify(observations.get(key))!==JSON.stringify(record))
      throw Error('MIXED_DISCOVERY_SNAPSHOT:'+file);
    observations.set(key,record);
    if(observations.size+directories.size>LIMIT) throw Error('TS_INPUT_SNAPSHOT_LIMIT');
    return value;
  }
  const fileExists = file => remember('file',file,ts.sys.fileExists(file));
  const directoryExists = file => remember('directory',file,ts.sys.directoryExists(file));
  const realpath = file => remember('realpath',file,normalize(ts.sys.realpath(file)));

  function entries(directory, record=true) {
    const files=[], dirs=[], captured=[];
    if(metadata(directory)) return {files,directories:dirs,captured};
    if(record) directoryExists(directory);
    let values;
    try { values=fs.readdirSync(directory,{withFileTypes:true}); }
    catch(error) {
      if(!['ENOENT','ENOTDIR'].includes(error.code)) throw error;
      values=[];
    }
    for(const entry of values) {
      if(entry.name==='.' || entry.name==='..') continue;
      const target=path.join(directory,entry.name);
      // The graph store is private output, never a compiler source directory.
      if(metadata(target)) continue;
      let stat=entry, link=null;
      if(entry.isSymbolicLink()) {
        link=fs.readlinkSync(target).split(path.sep).join('/');
        try { stat=fs.statSync(target); }
        catch(error) { if(error.code!=='ENOENT') throw error; stat=null; }
      }
      const kind=stat?.isFile()?'file':stat?.isDirectory()?'directory':'other';
      captured.push([entry.name,kind,link]);
      if(kind==='file') files.push(entry.name);
      else if(kind==='directory') dirs.push(entry.name);
    }
    captured.sort((a,b)=>order(a[0],b[0]));
    const key=normalize(directory), value={path:key,entries:captured};
    if(record) {
      if(directories.has(key) && JSON.stringify(directories.get(key))!==JSON.stringify(value))
        throw Error('MIXED_DISCOVERY_SNAPSHOT:'+directory);
      if(!directories.has(key)) entryCount+=captured.length;
      directories.set(key,value);
      if(observations.size+directories.size>LIMIT || entryCount>ENTRY_LIMIT) throw Error('TS_INPUT_SNAPSHOT_LIMIT');
    }
    files.sort();dirs.sort();
    return {files,directories:dirs,captured};
  }
  const host = {
    fileExists,directoryExists,realpath,
    readFile(file) {
      if(metadata(file)) throw Error('TS_ANALYSIS_METADATA_INPUT_UNSUPPORTED:'+file);
      fileExists(file);
      const value=readInput(file);
      fileExists(file);
      return value;
    },
    readDirectory(directory,extensions,excludes,includes,depth) {
      return ts.matchFiles(directory,extensions,excludes,includes,ts.sys.useCaseSensitiveFileNames,
        ts.sys.getCurrentDirectory(),depth,entries,realpath);
    },
    getDirectories(directory) { return entries(directory).directories; },
  };
  function lockfiles(configs) {
    const parents=new Set([root]);
    for(const config of configs) {
      for(let directory=path.dirname(config);;directory=path.dirname(directory)) {
        parents.add(directory);
        if(path.relative(root,directory)==='' || directory===path.dirname(directory)) break;
      }
    }
    for(const directory of parents) for(const name of ['package.json','package-lock.json','npm-shrinkwrap.json','pnpm-lock.yaml','yarn.lock','bun.lock','bun.lockb']) {
      const file=path.join(directory,name);
      if(fileExists(file)) host.readFile(file);
    }
  }
  function snapshot() {
    return {version:1,case_sensitive:ts.sys.useCaseSensitiveFileNames,
      observations:[...observations.values()].sort((a,b)=>order(a.op+'\0'+a.path,b.op+'\0'+b.path)),
      directories:[...directories.values()].sort((a,b)=>order(a.path,b.path))};
  }
  function validate() {
    for(const record of observations.values()) {
      const value=record.op==='file'?ts.sys.fileExists(record.path):record.op==='directory'?ts.sys.directoryExists(record.path):normalize(ts.sys.realpath(record.path));
      if(value!==record.value) throw Error('MIXED_DISCOVERY_SNAPSHOT:'+record.path);
    }
    for(const record of directories.values()) {
      if(JSON.stringify(record.entries)!==JSON.stringify(entries(record.path,false).captured))
        throw Error('MIXED_DISCOVERY_SNAPSHOT:'+record.path);
    }
  }
  return {host,lockfiles,snapshot,validate};
}
module.exports={inputSnapshot};
