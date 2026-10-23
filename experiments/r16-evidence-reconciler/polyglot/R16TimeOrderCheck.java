import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.regex.Pattern;

/** Offline independent Java reference for timestamp ordering only.
 * Does not authenticate ChatGPT run IDs or perform network calls.
 * Design reference: Temporal's distinction of Workflow ID and Run ID.
 */
public final class R16TimeOrderCheck {
    private static final Pattern EXACT_HOUR = Pattern.compile(
        "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:00:00(?:\\.0+)?(?:Z|[+-]\\d{2}:\\d{2})$");
    private static final Pattern ISO9 = Pattern.compile(
        "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d{1,9})?(?:Z|[+-]\\d{2}:\\d{2})$");
    private static Instant instant(String input) {
        if (!ISO9.matcher(input).matches()) return null;
        try {
            return OffsetDateTime.parse(input, DateTimeFormatter.ISO_OFFSET_DATE_TIME).toInstant();
        } catch (DateTimeParseException e) {
            return null;
        }
    }
    private static String verdict(String slot, String start, String end, String observed) {
        if (!EXACT_HOUR.matcher(slot).matches()) return "REJECT";
        Instant scheduled = instant(slot), a = instant(start), b = instant(end), c = instant(observed);
        if (scheduled == null || a == null || b == null || c == null) return "REJECT";
        Instant limit = scheduled.plusSeconds(3600);
        return !a.isBefore(scheduled) && !b.isBefore(a) && !b.isAfter(limit)
            && !c.isBefore(a) && !c.isAfter(b) ? "FORMAT" : "REJECT";
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Provide fixtures/time_cases.tsv");
        List<String> lines = Files.readAllLines(Path.of(args[0]), StandardCharsets.UTF_8);
        int passed = 0;
        for (int i = 1; i < lines.size(); i++) {
            String[] v = lines.get(i).split("\t", -1);
            if (v.length != 6) throw new AssertionError("Bad TSV row " + (i + 1));
            String actual = verdict(v[1], v[2], v[3], v[4]);
            if (!actual.equals(v[5])) throw new AssertionError(v[0] + ": expected " + v[5] + " actual " + actual);
            passed++;
        }
        System.out.println("JAVA time-order fixtures PASS " + passed + "/" + (lines.size() - 1));
    }
}
