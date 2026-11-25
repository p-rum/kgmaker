package org.kgmaker.excel;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.commons.compress.archivers.zip.ZipArchiveEntry;
import org.apache.poi.EncryptedDocumentException;
import org.apache.poi.hssf.OldExcelFormatException;
import org.apache.poi.hssf.record.Record;
import org.apache.poi.hssf.usermodel.HSSFSheet;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.openxml4j.exceptions.InvalidFormatException;
import org.apache.poi.openxml4j.opc.OPCPackage;
import org.apache.poi.openxml4j.opc.TargetMode;
import org.apache.poi.openxml4j.opc.ZipPackagePart;
import org.apache.poi.openxml4j.util.ZipFileZipEntrySource;
import org.apache.poi.openxml4j.util.ZipSecureFile;
import org.apache.poi.util.XMLHelper;
import org.w3c.dom.Element;
import org.apache.poi.poifs.filesystem.DirectoryNode;
import org.apache.poi.poifs.filesystem.EntryUtils;
import org.apache.poi.poifs.filesystem.POIFSFileSystem;
import org.apache.poi.poifs.macros.VBAMacroReader;
import org.apache.poi.ss.formula.WorkbookEvaluator;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.ss.usermodel.DateUtil;
import org.apache.poi.ss.usermodel.Name;
import org.apache.poi.ss.usermodel.FormulaError;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.apache.poi.xssf.model.ExternalLinksTable;
import org.apache.poi.xssf.usermodel.XSSFCell;
import org.apache.poi.xssf.usermodel.XSSFRelation;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

public final class ExcelWorker {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String VBA_REL =
        "http://schemas.microsoft.com/office/2006/relationships/vbaProject";
    private static final int MAX_CELLS = 100_000;
    private static final int MAX_VBA = 4 * 1024 * 1024;
    private static final int MAX_VML = 8 * 1024 * 1024;
    private static final String PAIRED_BREAK = "<br></br>";
    private static final Pattern VML_BREAK_MARKUP = Pattern.compile(
        "<!--.*?(?:-->|\\z)|<!\\[CDATA\\[.*?(?:\\]\\]>|\\z)|<\\?.*?(?:\\?>|\\z)|" + PAIRED_BREAK,
        Pattern.DOTALL);

    private ExcelWorker() {}

    public static void main(String[] args) throws IOException {
        ObjectNode response = JSON.createObjectNode();
        response.put("protocol_version", 1);
        response.put("worker", "excel-poi-6.0.0-2");
        response.putArray("capabilities").add("biff8").add("ooxml").add("vba");
        response.put("status", "OK");
        ArrayNode problems = response.putArray("diagnostics");
        try (var input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            JsonNode request = JSON.readTree(input.readLine());
            if (request.path("protocol_version").asInt() != 1
                || !request.path("operation").asText().equals("analyze")) {
                throw new IOException("Invalid operation");
            }
            String format = request.path("format").asText();
            if (!format.equals("xls") && !format.equals("xlsm") && !format.equals("xlsx")) {
                throw new IOException("Invalid format");
            }
            readWorkbook(Path.of("input." + format), format, response, problems);
        } catch (EncryptedDocumentException failure) {
            reject(response, "EXCEL_ENCRYPTED");
        } catch (OldExcelFormatException failure) {
            reject(response, "EXCEL_BIFF_UNSUPPORTED");
        } catch (Exception failure) {
            reject(response, "EXCEL_PARSE_FAILED");
        }
        JSON.writeValue(System.out, response);
    }

    private static void reject(ObjectNode response, String code) {
        response.remove("facts");
        response.put("status", "REJECTED");
        diagnostic((ArrayNode) response.get("diagnostics"), code, null, null);
    }

    private static void diagnostic(ArrayNode out, String code, String sheet, String cell) {
        ObjectNode value = out.addObject().put("code", code);
        if (sheet != null) value.put("sheet", sheet);
        if (cell != null) value.put("cell", cell);
    }

    private static final class VmlZipEntries extends ZipFileZipEntrySource {
        private final Set<ZipArchiveEntry> drawings = new HashSet<>();

        VmlZipEntries(ZipSecureFile archive) {
            super(archive);
        }

        @Override
        public InputStream getInputStream(ZipArchiveEntry entry) throws IOException {
            InputStream input = super.getInputStream(entry);
            if (!drawings.contains(entry)) return input;
            try (input) {
                byte[] bytes = input.readNBytes(MAX_VML + 1);
                if (bytes.length > MAX_VML) throw new IOException("VML drawing exceeds 8 MiB");
                // POI replaces literal <br> with <br/> before parsing VML, which leaves a
                // stray </br> for the valid paired form. ISO-8859-1 preserves the source bytes.
                String markup = new String(bytes, StandardCharsets.ISO_8859_1);
                if (!markup.contains(PAIRED_BREAK)) return new ByteArrayInputStream(bytes);
                String normalized = VML_BREAK_MARKUP.matcher(markup).replaceAll(match ->
                    match.group().equals(PAIRED_BREAK) ? "<br/>" : Matcher.quoteReplacement(match.group()));
                return new ByteArrayInputStream(normalized.getBytes(StandardCharsets.ISO_8859_1));
            }
        }
    }

    private static Workbook openWorkbook(Path path, String format) throws IOException, InvalidFormatException {
        if (format.equals("xls")) return WorkbookFactory.create(path.toFile(), null, true);
        var entries = new VmlZipEntries(new ZipSecureFile(path.toFile()));
        try {
            // A custom ZipEntrySource opens the OPC package read-only and keeps POI ZIP limits.
            OPCPackage pkg = OPCPackage.open(entries);
            for (var part : pkg.getPartsByContentType(XSSFRelation.VML_DRAWINGS.getContentType())) {
                if (part instanceof ZipPackagePart zipPart) entries.drawings.add(zipPart.getZipArchive());
            }
            return new XSSFWorkbook(pkg);
        } catch (IOException | InvalidFormatException | RuntimeException failure) {
            try {
                entries.close();
            } catch (IOException closeFailure) {
                failure.addSuppressed(closeFailure);
            }
            throw failure;
        }
    }

    private static void readWorkbook(Path path, String format, ObjectNode response, ArrayNode problems)
        throws Exception {
        if (format.equals("xls")) {
            inspectBiff(path, problems);
        } else {
            try (var input = java.nio.file.Files.newInputStream(path)) {
                if (org.apache.poi.poifs.filesystem.FileMagic.valueOf(input.readNBytes(8))
                    == org.apache.poi.poifs.filesystem.FileMagic.OLE2) {
                    try (var storage = new POIFSFileSystem(path.toFile(), true)) {
                        reject(response, storage.getRoot().hasEntry("EncryptedPackage")
                            ? "EXCEL_ENCRYPTED" : "EXCEL_FORMAT_MISMATCH");
                        return;
                    }
                }
            }
        }
        try (Workbook book = openWorkbook(path, format)) {
            if (format.equals("xls") != (book instanceof HSSFWorkbook)) {
                reject(response, "EXCEL_FORMAT_MISMATCH");
                return;
            }
            if (book instanceof XSSFWorkbook xssf
                && format.equals("xlsm") != xssf.isMacroEnabled()) {
                reject(response, "EXCEL_FORMAT_MISMATCH");
                return;
            }
            ObjectNode facts = response.putObject("facts");
            var builtinFunctions = new TreeSet<>(WorkbookEvaluator.getSupportedFunctionNames());
            builtinFunctions.addAll(WorkbookEvaluator.getNotSupportedFunctionNames());
            ArrayNode builtinNames = facts.putArray("builtin_functions");
            builtinFunctions.forEach(builtinNames::add);
            ArrayNode sheets = facts.putArray("sheets");
            ArrayNode names = facts.putArray("names");
            ArrayNode cells = facts.putArray("cells");
            ArrayNode tables = facts.putArray("tables");
            ArrayNode triggers = facts.putArray("triggers");
            ObjectNode externalLinks = facts.putObject("links");
            if (book instanceof XSSFWorkbook xssf) {
                var properties = xssf.getCTWorkbook().getWorkbookPr();
                if (properties != null) put(facts, "code_name", properties.getCodeName());
                facts.put("date_1904", xssf.isDate1904());
                readExternalLinks(xssf, externalLinks, problems);
                for (var part : xssf.getPackage().getParts()) {
                    String type = part.getContentType().toLowerCase(Locale.ROOT);
                    if (type.contains("macrosheet")) diagnostic(problems, "EXCEL_XLM_UNSUPPORTED", null, null);
                    if (type.contains("activex") || type.contains("vbaprojectsignature")) {
                        diagnostic(problems, "EXCEL_EMBEDDED_COMPONENT", null, null);
                    }
                    if (type.contains("connections") || type.contains("querytable")) {
                        diagnostic(problems, "EXCEL_DATA_CONNECTION", null, null);
                    }
                }
            } else if (book instanceof HSSFWorkbook hssf) {
                put(facts, "code_name", biffCodeName(hssf.getWorkbook().findFirstRecordBySid((short) 0x01ba)));
                facts.put("date_1904", hssf.getWorkbook().isUsing1904DateWindowing());
            }
            for (Name name : book.getAllNames()) {
                ObjectNode item = names.addObject().put("name", name.getNameName());
                put(item, "sheet", name.getSheetIndex() < 0 ? null : book.getSheetName(name.getSheetIndex()));
                try {
                    put(item, "formula", name.getRefersToFormula());
                } catch (RuntimeException failure) {
                    diagnostic(problems, "EXCEL_NAME_UNREADABLE", item.path("sheet").asText(null), null);
                }
            }
            boolean capped = false;
            for (int i = 0; i < book.getNumberOfSheets(); i++) {
                Sheet sheet = book.getSheetAt(i);
                ObjectNode item = sheets.addObject().put("name", sheet.getSheetName())
                    .put("visibility", book.getSheetVisibility(i).name());
                if (sheet instanceof XSSFSheet xssf) {
                    var properties = xssf.getCTWorksheet().getSheetPr();
                    if (properties != null) put(item, "code_name", properties.getCodeName());
                    readControls(xssf, triggers, problems);
                    for (var table : xssf.getTables()) {
                        tables.addObject().put("name", table.getName()).put("sheet", sheet.getSheetName())
                            .put("range", table.getCellReferences().formatAsString());
                    }
                } else if (sheet instanceof HSSFSheet hssf) {
                    put(item, "code_name", biffCodeName(hssf.getSheet().findFirstRecordBySid((short) 0x01ba)));
                    if (hssf.getSheet().findFirstRecordBySid((short) 0x00ec) != null
                        || hssf.getSheet().findFirstRecordBySid((short) 0x005d) != null) {
                        diagnostic(problems, "EXCEL_DRAWING_BINDINGS_UNRESOLVED", sheet.getSheetName(), null);
                    }
                }
                if (capped) continue;
                for (Row row : sheet) {
                    for (Cell cell : row) {
                        if (cells.size() >= MAX_CELLS) {
                            diagnostic(problems, "EXCEL_CELL_LIMIT", sheet.getSheetName(), cell.getAddress().formatAsString());
                            capped = true;
                            break;
                        }
                        if (cell.getCellType() != CellType.BLANK) addCell(cells, problems, cell);
                    }
                    if (capped) break;
                }
            }
            readVba(path, book, format, facts.putArray("modules"), problems);
        }
    }

    private static void readExternalLinks(XSSFWorkbook book, ObjectNode links, ArrayNode problems) {
        if (!book.getCTWorkbook().isSetExternalReferences()) return;
        var references = book.getCTWorkbook().getExternalReferences().getExternalReferenceArray();
        for (int index = 0; index < references.length; index++) {
            // Preserve the formula's index even when an earlier table is broken.
            try {
                if (book.getRelationById(references[index].getId()) instanceof ExternalLinksTable table) {
                    String identity = table.getLinkedFileName();
                    if (identity != null && !identity.isBlank()) {
                        links.put(Integer.toString(index + 1), identity);
                        continue;
                    }
                }
            } catch (RuntimeException ignored) {
                // Keep the workbook structure and report the unavailable link.
            }
            diagnostic(problems, "EXCEL_EXTERNAL_LINK_UNREADABLE", null, null);
        }
    }

    private static String biffCodeName(Record record) {
        if (record == null) return null;
        byte[] raw = record.serialize(); // BIFF header followed by XLUnicodeString.
        if (raw.length < 7) return null;
        int length = unsignedShort(raw, 4);
        boolean wide = (raw[6] & 1) != 0;
        int bytes = length * (wide ? 2 : 1);
        if (length > 31 || raw.length < 7 + bytes) return null;
        return new String(raw, 7, bytes, wide ? StandardCharsets.UTF_16LE : StandardCharsets.ISO_8859_1);
    }

    private static void readControls(XSSFSheet sheet, ArrayNode triggers, ArrayNode problems) {
        var part = sheet.getPackagePart();
        String ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/";
        String drawing = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing";
        String vml = "urn:schemas-microsoft-com:vml";
        String excel = "urn:schemas-microsoft-com:office:excel";
        try {
            for (String type : new String[] {"drawing", "vmlDrawing"}) {
                for (var relation : part.getRelationshipsByType(ns + type)) {
                    if (relation.getTargetMode() != TargetMode.INTERNAL) {
                        diagnostic(problems, "EXCEL_DRAWING_BINDINGS_UNRESOLVED", sheet.getSheetName(), null);
                        continue;
                    }
                    try (var input = part.getRelatedPart(relation).getInputStream()) {
                        var root = XMLHelper.newDocumentBuilder().parse(input);
                        var shapes = root.getElementsByTagNameNS(type.equals("drawing") ? drawing : vml,
                                                                  type.equals("drawing") ? "sp" : "shape");
                        for (int index = 0; index < shapes.getLength(); index++) {
                            var shape = (Element) shapes.item(index);
                            String macro = shape.getAttribute("macro");
                            if (type.equals("vmlDrawing")) {
                                var links = shape.getElementsByTagNameNS(excel, "FmlaMacro");
                                if (links.getLength() == 1) macro = links.item(0).getTextContent();
                            }
                            if (!macro.isBlank() && macro.length() <= 1024) {
                                triggers.addObject().put("sheet", sheet.getSheetName())
                                    .put("control", relation.getId() + "/" + (index + 1))
                                    .put("macro", macro.trim());
                            }
                        }
                    }
                }
            }
        } catch (Exception failure) {
            diagnostic(problems, "EXCEL_DRAWING_BINDINGS_UNRESOLVED", sheet.getSheetName(), null);
        }
    }

    private static void addCell(ArrayNode cells, ArrayNode problems, Cell cell) {
        String address = cell.getAddress().formatAsString();
        String sheet = cell.getSheet().getSheetName();
        CellType type = cell.getCellType();
        ObjectNode item = cells.addObject().put("sheet", sheet).put("cell", address).put("type", type.name());
        if (type == CellType.FORMULA) {
            try {
                item.put("formula", cell.getCellFormula());
            } catch (RuntimeException failure) {
                diagnostic(problems, "EXCEL_FORMULA_UNREADABLE", sheet, address);
            }
            CellType cached = cell.getCachedFormulaResultType();
            item.put("cached_type", cached.name());
            item.put("cached_freshness", "UNKNOWN");
            if (!(cell instanceof XSSFCell xssf) || xssf.getCTCell().isSetV()) {
                cellValue(item, "cached_value", cell, cached);
            }
        } else {
            cellValue(item, "value", cell, type);
        }
        var style = cell.getCellStyle();
        if (style != null && DateUtil.isADateFormat(style.getDataFormat(), style.getDataFormatString())) {
            item.put("date_format", true);
        }
    }

    private static void cellValue(ObjectNode object, String name, Cell cell, CellType type) {
        switch (type) {
            case NUMERIC -> {
                double value = cell.getNumericCellValue();
                if (Double.isFinite(value)) object.put(name, value);
            }
            case STRING -> object.put(name, cell.getStringCellValue());
            case BOOLEAN -> object.put(name, cell.getBooleanCellValue());
            case ERROR -> object.put(name, FormulaError.forInt(cell.getErrorCellValue()).getString());
            default -> { }
        }
    }

    private static void inspectBiff(Path path, ArrayNode problems) throws IOException {
        try (var storage = new POIFSFileSystem(path.toFile(), true);
             var stream = storage.createDocumentInputStream("Workbook")) {
            boolean first = true;
            for (byte[] head; (head = stream.readNBytes(4)).length == 4; ) {
                int sid = unsignedShort(head, 0);
                int size = unsignedShort(head, 2);
                byte[] bytes = stream.readNBytes(size);
                if (bytes.length != size) throw new IOException("Truncated BIFF record");
                if (first && (sid != 0x0809 || size < 4 || unsignedShort(bytes, 0) != 0x0600)) {
                    throw new OldExcelFormatException("BIFF8 required");
                }
                first = false;
                if (sid == 0x002f) throw new EncryptedDocumentException("Encrypted BIFF");
                if (sid == 0x0085 && size >= 6 && bytes[5] == 1) {
                    diagnostic(problems, "EXCEL_XLM_UNSUPPORTED", null, null);
                }
                if (sid == 0x00ec || sid == 0x005d) {
                    diagnostic(problems, "EXCEL_DRAWING_BINDINGS_UNRESOLVED", null, null);
                }
                if (sid == 0x000a) break;
            }
        }
    }

    private static int unsignedShort(byte[] bytes, int offset) {
        return (bytes[offset] & 255) | ((bytes[offset + 1] & 255) << 8);
    }

    private static void readVba(Path path, Workbook book, String format, ArrayNode out, ArrayNode problems) {
        VBAMacroReader.setMaxStringLength(MAX_VBA);
        try {
            if (book instanceof XSSFWorkbook xssf) {
                var part = xssf.getPackagePart();
                var links = part.getRelationshipsByType(VBA_REL);
                if (links.size() == 0) return;
                if (links.size() != 1 || format.equals("xlsx") || links.getRelationship(0).getTargetMode() != TargetMode.INTERNAL) {
                    diagnostic(problems, "EXCEL_VBA_RELATIONSHIP_UNSUPPORTED", null, null);
                    return;
                }
                try (InputStream input = part.getRelatedPart(links.getRelationship(0)).getInputStream();
                     var reader = new VBAMacroReader(input)) {
                    readModules(reader, out, problems);
                }
            } else {
                try (var storage = new POIFSFileSystem(path.toFile(), true);
                     var isolated = new POIFSFileSystem()) {
                    if (!storage.getRoot().hasEntry("_VBA_PROJECT_CUR")) return;
                    var project = (DirectoryNode) storage.getRoot().getEntry("_VBA_PROJECT_CUR");
                    EntryUtils.copyNodes(project, isolated.getRoot());
                    try (var reader = new VBAMacroReader(isolated)) {
                        readModules(reader, out, problems);
                    }
                }
            }
        } catch (Exception failure) {
            out.removeAll();
            diagnostic(problems, "EXCEL_VBA_UNREADABLE", null, null);
        }
    }

    private static void readModules(VBAMacroReader reader, ArrayNode out, ArrayNode problems) throws IOException {
        int total = 0;
        var modules = new TreeMap<>(reader.readMacroModules());
        if (modules.isEmpty()) diagnostic(problems, "EXCEL_VBA_UNREADABLE", null, null);
        for (var entry : modules.entrySet()) {
            var module = entry.getValue();
            String source = module.getContent();
            if (source == null || source.length() > MAX_VBA - total) {
                diagnostic(problems, "EXCEL_VBA_LIMIT", null, null);
                continue;
            }
            total += source.length();
            ObjectNode item = out.addObject().put("name", entry.getKey()).put("source", source);
            if (module.geModuleType() != null) item.put("type", module.geModuleType().name());
        }
    }

    private static void put(ObjectNode object, String field, String value) {
        if (value != null && !value.isEmpty()) object.put(field, value);
    }
}
