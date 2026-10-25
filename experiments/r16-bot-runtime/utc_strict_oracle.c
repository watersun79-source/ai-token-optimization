/* Isolated C11 UTC timestamp validator.
 * No network, credentials, subprocesses or native ChatGPT attestation.
 * Checks shared Python/Java/JavaScript TSV fixture without mutating it.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

static bool digits(const char *s, size_t start, size_t count) {
    for (size_t i = start; i < start + count; ++i) {
        if (s[i] < '0' || s[i] > '9') return false;
    }
    return true;
}

static unsigned number(const char *s, size_t start, size_t count) {
    unsigned value = 0;
    for (size_t i = start; i < start + count; ++i) {
        value = value * 10U + (unsigned)(s[i] - '0');
    }
    return value;
}

static bool leap(unsigned year) {
    return year % 4U == 0U && (year % 100U != 0U || year % 400U == 0U);
}

static bool strict_utc_timestamp(const char *s) {
    const size_t len = strlen(s);
    if (len < 20U || len > 35U) return false;
    if (s[4] != '-' || s[7] != '-' || s[10] != 'T'
            || s[13] != ':' || s[16] != ':') return false;
    if (!digits(s, 0, 4) || !digits(s, 5, 2) || !digits(s, 8, 2)
            || !digits(s, 11, 2) || !digits(s, 14, 2) || !digits(s, 17, 2)) {
        return false;
    }
    const unsigned year = number(s, 0, 4), month = number(s, 5, 2);
    const unsigned day = number(s, 8, 2), hours = number(s, 11, 2);
    const unsigned minutes = number(s, 14, 2), seconds = number(s, 17, 2);
    const unsigned month_days[12] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (year == 0U || month < 1U || month > 12U
            || hours > 23U || minutes > 59U || seconds > 59U) return false;
    const unsigned max_days = month_days[month - 1U] + ((month == 2U && leap(year)) ? 1U : 0U);
    if (day == 0U || day > max_days) return false;

    size_t pos = 19U;
    if (s[pos] == '.') {
        ++pos;
        const size_t begin = pos;
        while (pos < len && s[pos] >= '0' && s[pos] <= '9') ++pos;
        if (pos == begin || pos - begin > 9U) return false;
    }
    if (pos + 1U == len && s[pos] == 'Z') return true;
    if (pos + 6U != len || (s[pos] != '+' && s[pos] != '-')
            || s[pos + 3U] != ':') return false;
    if (!digits(s, pos + 1U, 2) || !digits(s, pos + 4U, 2)) return false;
    const unsigned offset_hour = number(s, pos + 1U, 2);
    const unsigned offset_minute = number(s, pos + 4U, 2);
    return offset_hour <= 18U && offset_minute <= 59U
           && (offset_hour < 18U || offset_minute == 0U);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fputs("usage: utc_strict_oracle FIXTURE.tsv\n", stderr);
        return 2;
    }
    FILE *file = fopen(argv[1], "r");
    if (file == NULL) {
        fputs("cannot read fixture\n", stderr);
        return 2;
    }
    char line[512];
    unsigned passed = 0U;
    if (fgets(line, sizeof line, file) == NULL
            || strcmp(line, "value\texpected\n") != 0) {
        fputs("invalid fixture header\n", stderr);
        fclose(file);
        return 2;
    }
    while (fgets(line, sizeof line, file) != NULL) {
        const size_t length = strlen(line);
        if (length == 0U || line[length - 1U] != '\n') {
            fputs("oversized or unterminated row\n", stderr);
            fclose(file);
            return 2;
        }
        line[length - 1U] = '\0';
        char *tab = strchr(line, '\t');
        if (tab == NULL || strchr(tab + 1, '\t') != NULL) {
            fputs("invalid row structure\n", stderr);
            fclose(file);
            return 2;
        }
        *tab = '\0';
        const char *expected = tab + 1;
        if (strcmp(expected, "PASS") != 0 && strcmp(expected, "FAIL") != 0) {
            fputs("invalid fixture expectation\n", stderr);
            fclose(file);
            return 2;
        }
        const bool valid = strict_utc_timestamp(line);
        if (strcmp(valid ? "PASS" : "FAIL", expected) != 0) {
            fprintf(stderr, "oracle mismatch on case %u\n", passed + 1U);
            fclose(file);
            return 1;
        }
        ++passed;
    }
    if (ferror(file) || fclose(file) != 0 || passed == 0U) {
        fputs("empty or unreadable fixture\n", stderr);
        return 2;
    }
    printf("C strict timestamp oracle: PASS %u/%u\n", passed, passed);
    return 0;
}
