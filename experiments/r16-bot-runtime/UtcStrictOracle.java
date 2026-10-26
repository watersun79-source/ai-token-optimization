import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Set;
import java.util.regex.Pattern;

public class UtcStrictOracle {
  static final int MAX_FIXTURE_BYTES = 65536;
  static final int MAX_FIXTURE_CASES = 256;
  static Pattern pat = Pattern.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})$");
  static boolean valid(String s) {
    if(!pat.matcher(s).matches())return false;
    try {
      OffsetDateTime dt=OffsetDateTime.parse(s,DateTimeFormatter.ISO_OFFSET_DATE_TIME);
      return dt.getYear()>0&&dt.getYear()<10000;
    } catch(Exception e) {return false;}
  }
  public static void main(String[] a)throws Exception{
    if(a.length>1)throw new IllegalArgumentException("Expected at most one fixture path");
    var fixture=a.length==1?Paths.get(a[0]):Paths.get("utc_strict_oracle_cases.tsv");
    if(Files.isSymbolicLink(fixture))throw new IllegalArgumentException("Fixture size or type invalid");
    byte[] raw;
    try(SeekableByteChannel channel=Files.newByteChannel(
        fixture, Set.of(StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS))){
      if(channel.size()>MAX_FIXTURE_BYTES)throw new IllegalArgumentException("Fixture size or type invalid");
      ByteBuffer data=ByteBuffer.allocate(MAX_FIXTURE_BYTES+1);
      while(data.hasRemaining() && channel.read(data)!=-1){}
      if(data.position()>MAX_FIXTURE_BYTES)throw new IllegalArgumentException("Fixture size or type invalid");
      raw=new byte[data.position()];
      data.flip();
      data.get(raw);
    }
    var lines=new String(raw, StandardCharsets.UTF_8).lines().toList();
    if(lines.size()<2 || !lines.get(0).equals("value\texpected"))throw new IllegalArgumentException("Invalid or empty fixture");
    if(lines.size()-1>MAX_FIXTURE_CASES)throw new IllegalArgumentException("Too many fixture cases");
    int n=0; for(String line:lines.subList(1,lines.size())){
      String[] fields=line.split("\t",-1);
      if(fields.length!=2 || !(fields[1].equals("PASS") || fields[1].equals("FAIL")))throw new IllegalArgumentException("Malformed case "+(n+1));
      boolean ok=valid(fields[0]);
      if(!fields[1].equals(ok?"PASS":"FAIL"))throw new RuntimeException("mismatch case "+(n+1));
      n++;
    }
    System.out.println("Java strict timestamp oracle: PASS "+n+"/"+n);
  }
}
