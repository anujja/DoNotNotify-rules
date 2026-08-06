// Compiles every extracted REGEX filter with java.util.regex — the engine
// DoNotNotify actually uses. Run scripts/validate.py first; it writes
// build/regexes.txt as "<source-label>\t<base64(pattern)>" lines.
//
// Usage: java scripts/ValidateRegex.java build/regexes.txt

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

public class ValidateRegex {
    public static void main(String[] args) throws Exception {
        Path input = Path.of(args.length > 0 ? args[0] : "build/regexes.txt");
        if (!Files.exists(input)) {
            System.err.println("missing " + input + " — run scripts/validate.py first");
            System.exit(1);
        }
        List<String> lines = Files.readAllLines(input, StandardCharsets.UTF_8);
        int checked = 0;
        int failures = 0;
        for (String line : lines) {
            if (line.isBlank()) continue;
            String[] parts = line.split("\t", 2);
            if (parts.length != 2) {
                System.err.println("FAIL malformed line: " + line);
                failures++;
                continue;
            }
            String pattern = new String(Base64.getDecoder().decode(parts[1]), StandardCharsets.UTF_8);
            checked++;
            try {
                Pattern.compile(pattern);
            } catch (PatternSyntaxException e) {
                failures++;
                System.err.println("FAIL " + parts[0] + ": " + e.getMessage().replace('\n', ' '));
            }
        }
        System.out.println(checked + " regex(es) compiled, " + failures + " failure(s)");
        if (failures > 0) System.exit(1);
    }
}
