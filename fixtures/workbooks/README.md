# Legacy spreadsheet diagnostic fixture

`legacy-biff2.xls` is a minimal standalone BIFF2 worksheet stream: BOF (version 2,
worksheet type), DIMENSIONS for one cell, NUMBER A1=42, EOF. Its 43 bytes are
binary records, not a ZIP/XML workbook. The tests use its real header and copy
the same bytes to `.xlsx` to verify rejection before the XLSX parser. KGMAKER
never reads or asserts that numeric value. It does not validate workbook integrity.

The fixture contains no macros, links or executable content. OLE compound-file
ambiguity and malformed inputs are separate inline test inputs; a compound-file
signature alone does not establish valid Excel content.
