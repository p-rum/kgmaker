# TypeScript effective config a obsahová freshness

T003-S08-W02 rozšiřuje existující compiler context, nikoli module resolver.
TypeScript5.7.3 nadále zpracovává `extends`, `baseUrl`, `paths`, `include`,
`exclude`, project references a compiler options. `exclude` omezuje root-file
objevování: soubor dosažený importem zůstává compiler input i při odpovídajícím
exclude patternu. Nic se neemituje a nespouští se npm, build ani aplikace.

## Snapshot a offline validace

Nový worker `typescript-worker-3` ukládá vedle existujících
`project.input_files` (absolute path/SHA-256) `project.input_discovery` v1:

- Výsledky skutečně provedených file/directory existence a realpath dotazů.
- Jména, druhy a symlink targety v compilerem navštívených adresářích. Matching
  globů provádí TypeScript `matchFiles`; provider nepřekládá TS globs do Pythonu.
- Obsah i nepřítomnost `package.json`, `package-lock.json`, `npm-shrinkwrap.json`,
  `pnpm-lock.yaml`, `yarn.lock`, `bun.lock` a `bun.lockb` v rootu a ancestor
  adresářích vybraných project configů uvnitř rootu.

Context marker je `source_snapshot_version=typescript-input-discovery-1`.
Provider pouze rehashuje zachycené soubory a opakuje filesystem observations;
nezavolá TypeScript, Node ani package manager. Timestamps nejsou freshness důkaz.
Změna relevantního extends/options/alias souboru, imported/excluded dependency,
nového include člena, dříve chybějící alias dependency nebo lockfile vrátí STALE.
Nezávislá config B nebo excluded-unused source A svým pouhým obsahem A nestalují.

Directory discovery zůstává konzervativní: změna členství navštíveného adresáře
může vyžádat reinspection i tehdy, když nová položka nakonec neovlivní resolution.
Nejde o persistent incremental compiler cache. Private `.kgmaker` je vlastní
analysis output; nevstupuje do discovery. Explicitní compiler vstup z tohoto
adresáře je unsupported, aby publikace grafu sama nestalovala svůj context.

Preflight a analysis musejí vrátit shodný positive closure i discovery snapshot;
pozorování se znovu ověří před publikací. Mixed/malformed/unknown-version data
nepřepíší poslední validní graf. Limity: nejvýše20 000 filesystem observations
plus directories, 20 000 positive files a100 000 directory entries. Překročení
je explicitní failure, nikdy COMPLETE. Symbol/call/protocol transport limity se
nemění. Snapshot helper je součástí wheel resources i distribution content hash.

## Kompatibilita a hranice

Legacy context bez nového markeru zachovává původní konzervativní source/config
snapshot. Reinspection používá stejný TS selector slot, včetně již podporovaných
legacy/K2-era selector variant. JVM selection/snapshots se nemění. Graph/store
v1/v2/v3 i protocol1 zůstávají čitelné; nový metadata objekt má vlastní verzi.
SOURCE_ONLY funguje bez compileru. SOURCE_ONLY, compiler evidence a runtime/data
availability zůstávají oddělené; tato změna nepotvrzuje runtime data ani celý S08.

Příklady:

```sh
kgmaker inspect frontend --root ./frontend --tsconfig tsconfig.app.json
kgmaker status --root ./frontend
# STALE diagnostika vrátí přesný explicitní inspect příkaz; status nic nebuildí.
```

Konkrétní skutečné testy a zbývající mezery eviduje
[change note45](changes/45_scopeTypeScriptConfigFreshness.md).

Lokální source-final matice nad main33dc: focused70PASS a full567PASS/10SKIP
(787.45s), genuine pinned worker/toolchain. Skip detaily a předchozí setup opravy
jsou v note45. GitHub Actions billing/quota blokuje nové CI; merge acceptance
není lokálním proof nahrazena. Windows/K2/exporter runtime support se tímto nemění.
