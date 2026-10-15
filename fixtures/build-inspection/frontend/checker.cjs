const ts = require('typescript');
const configPath = __dirname + '/tsconfig.json';
const raw = ts.readConfigFile(configPath, ts.sys.readFile);
if (raw.error) throw new Error(ts.flattenDiagnosticMessageText(raw.error.messageText, '\n'));
const config = ts.parseJsonConfigFileContent(raw.config, ts.sys, __dirname);
const program = ts.createProgram({rootNames: config.fileNames, options: config.options});
const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length) {
  process.stderr.write(ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCanonicalFileName: p => p, getCurrentDirectory: () => __dirname, getNewLine: () => '\n'
  }));
  process.exit(1);
}
const checker = program.getTypeChecker();
const calls = [];
for (const source of program.getSourceFiles()) {
  if (!config.fileNames.includes(source.fileName)) continue;
  function visit(node) {
    if (ts.isCallExpression(node) && node.expression.getText(source) === 'process') {
      const signature = checker.getResolvedSignature(node);
      const declaration = signature.getDeclaration();
      const position = source.getLineAndCharacterOfPosition(node.getStart(source));
      calls.push({file:source.fileName,line:position.line+1,
                  target:checker.getFullyQualifiedName(checker.getSymbolAtLocation(node.expression)),
                  signature:checker.signatureToString(signature),
                  declaration:declaration.getText(source)});
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
}
if (calls.length !== 2 || !calls.some(c => c.signature === '(value: number): string') ||
    !calls.some(c => c.signature === '(value: string): string')) throw new Error('Incorrect overload resolution');
process.stdout.write(JSON.stringify({compiler:ts.version,status:'PASS',calls},null,2)+'\n');
