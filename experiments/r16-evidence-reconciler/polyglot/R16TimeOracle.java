// Independent format-only time oracle. NOT a ChatGPT scheduler authenticator.
// Built with OpenJDK java.time; no network, SDK, credentials or provider APIs.
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.regex.Pattern;

public final class R16TimeOracle {
  private static final Pattern TIME = Pattern.compile(
      "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})");
  private static final Pattern HOUR = Pattern.compile(
      "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:00:00(?:\\.0+)?(?:Z|[+-][0-9]{2}:[0-9]{2})");

  private static Instant parseTime(String raw) {
    if (raw == null || !TIME.matcher(raw).matches()) return null;
    try { return OffsetDateTime.parse(raw).toInstant(); }
    catch (DateTimeParseException exception) { return null; }
  }

  public static boolean formatMatches(String slotRaw, String startRaw, String endRaw, String observedRaw) {
    if (slotRaw == null || !HOUR.matcher(slotRaw).matches()) return false;
    Instant slot = parseTime(slotRaw);
    Instant start = parseTime(startRaw);
    Instant end = parseTime(endRaw);
    Instant observed = parseTime(observedRaw);
    if (slot == null || start == null || end == null || observed == null) return false;
    Instant hourEnd = slot.plus(Duration.ofHours(1));
    return !start.isBefore(slot) && !end.isBefore(start) && !end.isAfter(hourEnd)
        && !observed.isBefore(start) && !observed.isAfter(end);
  }

  public static void main(String[] args) throws Exception {
    if (args.length != 1) throw new IllegalArgumentException("Provide one local TSV fixture file");
    List<String> lines = Files.readAllLines(Path.of(args[0]), StandardCharsets.UTF_8);
    int passed = 0;
    int total = 0;
    for (String line : lines) {
      if (line.isBlank() || line.startsWith("#")) continue;
      String[] columns = line.split("\\|", -1);
      if (columns.length != 6) throw new IllegalArgumentException("Malformed local fixture row");
      total++;
      boolean actual = formatMatches(columns[1], columns[2], columns[3], columns[4]);
      boolean expected = switch (columns[5]) {
        case "PASS" -> true;
        case "REJECT" -> false;
        default -> throw new IllegalArgumentException("Bad expected outcome");
      };
      if (actual != expected) throw new AssertionError("Mismatch: " + columns[0]);
      passed++;
    }
    System.out.println("R16 Java time oracle: " + passed + "/" + total + " format cases PASS; AUTHENTICITY=UNVERIFIED");
  }
}
