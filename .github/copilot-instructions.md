# Vývoj repozitáře KGMAKER

Řiď se `AGENTS.md`, `docs/tasks/README.md`, příslušným zadáním a aktuálním
zdrojovým kódem. Před změnou čti dotčené moduly, jejich volající a testy pomocí
`rg`, běžných souborových nástrojů a Gitu. Stavové dokumenty jsou evidence
konkrétních revizí, nikoli náhrada ověření současného zdroje.

KGMAKER se v tomto repozitáři nepoužívá na vlastní vývoj. Nespouštěj zde
indexování, semantic/memory ani task/workflow/completion postupy. Neinstaluj
sem cílové hooky, agenty nebo skilly a neobnovuj vlastní `.kgmaker/` graf.
Starší pokyny k self-use jsou nahrazeny uživatelským rozhodnutím z 2026-11-24.
Distribuované Python templates zůstávají určeny pro jiné cílové projekty.
Příkazy a API produktu testuj na oddělených fixture/dočasných projektech.

Pro každý krok zaznamenej zadání/acceptance, výchozí SHA, skutečný diff,
příkazy a výsledky PASS/FAIL/SKIP/NOT_RUN přímo do českého change note.
Ověř relevantní testy, kompatibilitu a `git diff --check`; chybějící toolchain
není PASS. Zachovej cizí rozpracované změny. Vývojové profily v `.codex/agents`
pracují přímo se zdroji a GitHub PR; T045 review/merge pravidla v AGENTS platí.

## Konvence T004 a jeho atomických úkolů

Pro T005–T044 platí uživatelská konvence `docs/tasks/T-<NNN>_<kebab-case-slug>.md`
ze dne 2026-10-20. Je to tatáž globální číselná řada T005–T044.
Další zadání používají formát z AGENTS; české change notes mají nezávislou
řadu `<N>_<lowerCamelCase>.md`. Publikovaná ID ani historii nepřečísluj.
