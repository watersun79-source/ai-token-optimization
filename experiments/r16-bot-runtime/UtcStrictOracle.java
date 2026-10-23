import java.io.*;
import java.nio.file.*;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.regex.Pattern;

public class UtcStrictOracle {
  static Pattern pat = Pattern.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})$");
  static boolean valid(String s) {
    if(!pat.matcher(s).matches())return false;
    try {
      OffsetDateTime dt=OffsetDateTime.parse(s,DateTimeFormatter.ISO_OFFSET_DATE_TIME);
      return dt.getYear()>0&&dt.getYear()<10000;
    } catch(Exception e) {return false;}
  }
  public static void main(String[] a)throws Exception{
    int n=0; for(String line:Files.readAllLines(Paths.get("utc_strict_oracle_cases.tsv")).subList(1,21)){
      String[] fields=line.split("\t"); boolean ok=valid(fields[0]);
      if(!fields[1].equals(ok?"PASS":"FAIL")) throw new RuntimeException("mismatch case "+(n+1)+" "+fields[0]);n++;
    }
    System.out.println("Java strict timestamp oracle: PASS "+n+"/"+n);
  }
}
