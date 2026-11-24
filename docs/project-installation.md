# Upgrade a odstranění KGMAKERu v cílovém projektu

Po instalaci nové verze Python balíčku aktualizuj projektové integrace:

```bash
kgmaker upgrade --root /cesta/k/projektu
```

Příkaz používá právě nainstalovanou distribuci. Aktualizuje její Copilot agenty,
hook, instrukce, Junie commands, Agent Skills a reference, editovatelné artifact
templates a spravovaná pravidla `.gitignore`. Doplní nové a chybějící výstupy,
odstraní známé vysloužilé výstupy. Neinstaluje Python balíček, nespouští aplikaci,
scan, compiler worker, testy ani migrace. Graf, historie analýz a vlastní
`.kgmaker/NOTES.md` zůstávají při upgradu zachované. Hostitel může vyžadovat reload.

```bash
# Volitelný náhled bez zápisů; konflikt má i zde exit 2:
kgmaker upgrade --root /cesta/k/projektu --dry-run
# Jen po kontrole konfliktů; zahodí místní úpravy spravovaných templates:
kgmaker upgrade --root /cesta/k/projektu --force
```

## Vlastnictví a konflikty

`init` vytváří `.kgmaker/install-manifest.json` ve schématu 1: verzi distribuce,
SHA-256 instalovaných souborů, seznam zachovaných cizích souborů a přesný text
přidaný do `.gitignore`. Manifest ponech v projektu a při přenosu integrace mezi
checkouty přenes i jej. Jeho ztráta znamená přechod na omezené legacy rozpoznání.
Opakovaný běžný `init` zachová existující obsah i mtime; upgrade je samostatná
operace. Template páry si při init zachovávají původní ochranu i s `--force`.

Upgrade přepíše soubor automaticky jen při shodě s posledním instalovaným
obsahem (nebo když už odpovídá nové verzi). Konflikty vypíše před zápisem a celý
plán zastaví s kódem 2. Uživatelské soubory zachované při init nepřebírá ani
`upgrade --force`. Vlastní změny slouč ručně; `--force` použij jen při úmyslném
zahození úprav spravovaných souborů. Poškozený manifest nebo změněný spravovaný
blok `.gitignore` nelze obejít pomocí force.

Staré instalace bez manifestu rozpoznávají pouze přesné známé otisky distribuce
na baseline `edb65e5` a aktuální templates. Neznámé historické verze či vlastní
úpravy znamenají konflikt; samotné jméno souboru není důkaz vlastnictví.
Explicitní force u legacy instalace může přepsat/smazat kolidující soubor na
známé integrační cestě, včetně `.github/copilot-instructions.md`; nejprve zkontroluj
náhled. Staré ignore záznamy se přebírají pouze po celých přesně známých řádcích.

## Kompletní odstranění z projektu

```bash
kgmaker uninstall --root /cesta/k/projektu --dry-run
kgmaker uninstall --root /cesta/k/projektu
# Pokud chceš odstranit i místně upravené spravované agenty/skilly/hooky:
kgmaker uninstall --root /cesta/k/projektu --force
```

Odstranění zahrnuje **celý `.kgmaker/`**, tedy grafy, compiler cache, konfiguraci,
poznámky, vlastní templates, workflow a historii analýz. Před spuštěním si
potřebná data ulož mimo tento adresář. Běžný uninstall navíc odmítne odstranit
upravené spravované integrační soubory mimo `.kgmaker`, dokud je nesloučíš nebo
nezvolíš force. Cizí agenty/skilly, aplikační zdroje a uživatelská pravidla ignore
zachová; prázdné rodičovské adresáře po vlastních souborech uklidí.

Python balíček v prostředí zůstává nainstalovaný. Uživatelské exporty vytvořené
mimo `.kgmaker/` (například vygenerovaný test či report) se nemažou. Neznámé ruční
integrace mimo explicitní inventář nemají automatické odstranění. Další uninstall
po úspěšném odstranění je bez změn.

## API, chyby a ověření

`kgmaker.cli.init(root, force=False)` zůstává zachované. Python API
`kgmaker.installation.run(root, 'upgrade' | 'uninstall', force=False, dry_run=False)`
vrací 0 při úspěchu, 2 při konfliktu, neplatném vstupu či I/O chybě. Root musí
být existující adresář. Výpis WRITE/REMOVE představuje plán, který se při konfliktu
neprovede; PRESERVE uvádí soubory zachované jako cizí.

Všechny spravované cesty mají preflight: symlink, speciální soubor či adresář
místo souboru je chyba i s force. Běžná zachytitelná chyba publikace obnoví
původní soubory pomocí přejmenovaných záloh. Při selhání samotné obnovy nebo úklidu
záloh příkaz vypíše cestu `.kgmaker-lifecycle-*` k ruční obnově/úklidu.
Není zaručena transakce při pádu procesu nebo výpadku napájení. Během příkazů
nespouštěj další zápisy do integrace či `.kgmaker/`.

Distribuované instrukce mají stále stejné zdroje v Python templates; žádné
aktivní spravované kopie se neinstalují do vývojového checkoutu. Nové výstupy
se přidávají do společného inventáře. Při vyřazování výstupu zachovej jeho cestu
a historické otisky v `installation_history.py`, aby ho šlo bezpečně odstranit.

[T053](tasks/53_manageProjectInstallation.md), [změna a provedené kontroly](changes/170_manageProjectInstallation.md).
Testy používají izolované cíle a wheel mimo checkout; živý reload hostitelů,
Windows a výpadek procesu nejsou tímto ověřeny. T049 hostitelské profily a
technické vynucení Git autorizace jsou samostatný rozsah.
