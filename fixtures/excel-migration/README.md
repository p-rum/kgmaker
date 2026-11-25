# Excel migration fixtures

The original BIFF8 `legacy.xls` is Apache POI's unmodified
[`SimpleMacro.xls`](https://github.com/apache/poi/blob/4793c3e741c2858bf29e728f13f617ee784243f4/test-data/spreadsheet/SimpleMacro.xls),
from Apache POI, licensed under Apache License 2.0. `migration.xlsm` derives
from the same revision's
[`SimpleMacro.xlsm`](https://github.com/apache/poi/blob/4793c3e741c2858bf29e728f13f617ee784243f4/test-data/spreadsheet/SimpleMacro.xlsm).
The [Apache POI notice](APACHE-POI-NOTICE.txt)
and repository Apache License apply to those source artifacts.

The generator replaces VBA source streams with synthetic examples and adds
formulas, an external reference, a named range, a hidden sheet and a drawing
action. It also creates `Rates.xlsx` and an encrypted variant. The XLSM is a
static parser fixture. Its source streams and compiled module caches have
different contents. Keep it out of Excel execution tests.

Regenerate after building the Excel worker. Download the pinned source XLSM
separately and pass its local path.

```sh
java -cp 'workers/excel/target/lib/*' fixtures/excel-migration/GenerateExcelFixtures.java /path/to/SimpleMacro.xlsm fixtures/excel-migration fixtures/excel-migration/migration.xlsm
```

POI ZIP timestamps and encryption salts can vary between regenerations.
Tests assert the observed business and dependency structure.
