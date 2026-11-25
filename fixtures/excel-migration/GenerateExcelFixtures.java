import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Arrays;
import org.apache.poi.openxml4j.opc.*;
import org.apache.poi.poifs.crypt.*;
import org.apache.poi.poifs.filesystem.*;
import org.apache.poi.ss.usermodel.SheetVisibility;
import org.apache.poi.util.RLEDecompressingInputStream;
import org.apache.poi.xssf.usermodel.*;

public class GenerateExcelFixtures {
    static void replaceModule(DirectoryNode vba, String name, String extra) throws IOException {
        byte[] original;
        try (var input = vba.createDocumentInputStream(name)) {
            original = input.readAllBytes();
        }
        for (int offset = 0; offset < original.length - 4; offset++) {
            if (original[offset] != 1 || (original[offset+2] & 0x70) != 0x30) continue;
            String decoded;
            try (var stream = new RLEDecompressingInputStream(
                    new ByteArrayInputStream(original, offset, original.length - offset))) {
                decoded = new String(stream.readAllBytes(), StandardCharsets.ISO_8859_1);
            } catch (RuntimeException | IOException invalid) { continue; }
            if (!decoded.startsWith("Attribute VB_Name = \"" + name + "\"")) continue;
            String attrs = decoded.lines().takeWhile(line -> line.startsWith("Attribute VB_"))
                .reduce("", (left, line) -> left + line + "\r\n");
            byte[] source = (attrs + extra.stripIndent().replace("\n", "\r\n")).getBytes(StandardCharsets.US_ASCII);
            ByteArrayOutputStream literals = new ByteArrayOutputStream();
            for (int i = 0; i < source.length; i += 8) {
                literals.write(0);
                literals.write(source, i, Math.min(source.length - i, 8));
            }
            int head = 0xb000 | (literals.size() - 1);
            ByteArrayOutputStream content = new ByteArrayOutputStream();
            content.write(original, 0, offset);
            content.write(1);
            content.write(head & 0xff);
            content.write(head >> 8);
            literals.writeTo(content);
            vba.createOrUpdateDocument(name, new ByteArrayInputStream(content.toByteArray()));
            return;
        }
        throw new IOException("Unable to replace " + name);
    }
    public static void main(String[] args) throws Exception {
        Path source = Path.of(args[0]), destination = Path.of(args[1]);
        Path edited = Path.of(args[2]);
        try (var workbook = new XSSFWorkbook(source.toFile());
             var dep = new XSSFWorkbook()) {
            dep.createSheet("Rates").createRow(1).createCell(1).setCellValue(0.25);
            try (var out = Files.newOutputStream(destination.resolve("Rates.xlsx"))) {
                dep.write(out);
            }

            var vbaLink = workbook.getPackagePart().getRelationshipsByType(
                "http://schemas.microsoft.com/office/2006/relationships/vbaProject").getRelationship(0);
            var project = workbook.getPackagePart().getRelatedPart(vbaLink);
            byte[] projectBytes;
            try (var input = project.getInputStream(); var fs = new POIFSFileSystem(input);
                 var rewritten = new ByteArrayOutputStream()) {
                var vba = (DirectoryNode) fs.getRoot().getEntry("VBA");
                replaceModule(vba, "ThisWorkbook", """
                    Private Sub Workbook_Open()
                        Call RecalculateInvoice
                    End Sub
                    """);
                replaceModule(vba, "Sheet1", """
                    Private Sub Worksheet_Change(ByVal Target As Range)
                        Me.Range("B5").Value2 = 1
                    End Sub
                    """);
                replaceModule(vba, "Module1", """
                    Public Sub RecalculateInvoice()
                        ThisWorkbook.Worksheets("Sheet1").Range("A1").Value2 = Workbooks("Rates.xlsx").Worksheets("Rates").Range("B2").Value2
                    End Sub
                    Public Function RoundExtra(ByVal Size As Double) As Double
                        RoundExtra = Size + 1
                    End Function
                    """);
                fs.writeFilesystem(rewritten);
                projectBytes = rewritten.toByteArray();
            }
            project.clear();
            try (var output = project.getOutputStream()) { output.write(projectBytes); }

            var sheet = workbook.getSheet("Sheet1");
            var amounts = sheet.getRow(0);
            amounts.createCell(1).setCellFormula("A1*2");
            amounts.createCell(2).setCellFormula("RoundExtra(A1)");
            workbook.linkExternalWorkbook("Rates.xlsx", dep);
            amounts.createCell(3).setCellFormula("[Rates.xlsx]Rates!$B$2+A1");
            var name = workbook.createName();
            name.setNameName("InvoiceTotal");
            name.setRefersToFormula("Sheet1!$B$1");
            workbook.setSheetVisibility(2, SheetVisibility.VERY_HIDDEN);
            var drawing = sheet.createDrawingPatriarch();
            var shape = drawing.createSimpleShape(new XSSFClientAnchor(0, 0, 10, 10, 4, 1, 6, 2));
            shape.getCTShape().setMacro("[0]!RecalculateInvoice");
            try (var output = Files.newOutputStream(edited)) {
                workbook.write(output);
            }
        }
        try (var fs = new POIFSFileSystem()) {
            var mode = new EncryptionInfo(EncryptionMode.agile);
            var encryptor = mode.getEncryptor();
            encryptor.confirmPassword("fixture-password");
            try (var out = encryptor.getDataStream(fs)) {
                Files.copy(destination.resolve("Rates.xlsx"), out);
            }
            try (var out = Files.newOutputStream(destination.resolve("encrypted.xlsx"))) {
                fs.writeFilesystem(out);
            }
        }
    }
}
