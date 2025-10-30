/*
 * inspect_spk.c - Детальный анализ SPK файлов через SPICE Toolkit
 *
 * Извлекает нативные интервалы Чебышёва для каждого тела.
 *
 * Компиляция (Windows, MSVC):
 *   cl /I..\vendor\spice\cspice\include inspect_spk.c ..\vendor\spice\cspice\lib\cspice.lib /Fe:inspect_spk.exe
 *
 * Компиляция (Windows, MinGW):
 *   gcc -I../vendor/spice/cspice/include inspect_spk.c -L../vendor/spice/cspice/lib -lcspice -o inspect_spk.exe
 *
 * Использование:
 *   inspect_spk.exe file.bsp
 */

#include <stdio.h>
#include <stdlib.h>
#include "SpiceUsr.h"

#define MAXOBJ 1000
#define MAXIVL 1000000

/* Имена тел */
typedef struct {
    int id;
    const char *name;
} BodyName;

BodyName BODY_NAMES[] = {
    {1, "Mercury"}, {2, "Venus"}, {3, "EMB"}, {4, "Mars"}, {5, "Jupiter"},
    {6, "Saturn"}, {7, "Uranus"}, {8, "Neptune"}, {9, "Pluto"}, {10, "Sun"},
    {199, "Mercury Barycenter"}, {299, "Venus Barycenter"},
    {301, "Moon"}, {399, "Earth"},
    {2000001, "Ceres"}, {2000002, "Pallas"}, {2000004, "Vesta"},
    {2000007, "Iris"}, {2000324, "Bamberga"},
    {2090377, "Sedna"}, {2136108, "Haumea"}, {2136199, "Eris"}, {2136472, "Makemake"},
    {0, NULL}
};

const char* get_body_name(int id) {
    for (int i = 0; BODY_NAMES[i].name != NULL; i++) {
        if (BODY_NAMES[i].id == id) {
            return BODY_NAMES[i].name;
        }
    }
    static char buf[32];
    sprintf(buf, "Body %d", id);
    return buf;
}

void analyze_segment(int handle, int body_id, double start, double end) {
    SpiceInt n;
    SpiceDouble descr[5];
    SpiceDouble dc[2];
    SpiceInt ic[6];
    SpiceBoolean found;

    /* Получаем дескриптор сегмента */
    dafgda_c(handle, 3, 7, descr);

    if (failed_c()) {
        reset_c();
        return;
    }

    /* Распаковываем дескриптор SPK Type 2 (Chebyshev) */
    spkuds_c(descr, &dc[0], &dc[1], &ic[0], &ic[1], &ic[2], &ic[3], &ic[4], &ic[5]);

    if (failed_c()) {
        reset_c();
        return;
    }

    /* ic[4] содержит начальный адрес данных */
    /* ic[5] содержит конечный адрес данных */

    int data_begin = ic[4];
    int data_end = ic[5];

    /* Читаем первые несколько значений для определения структуры */
    SpiceDouble data[100];
    int nread = (data_end - data_begin + 1 > 100) ? 100 : (data_end - data_begin + 1);

    dafgda_c(handle, data_begin, data_begin + nread - 1, data);

    if (failed_c()) {
        reset_c();
        return;
    }

    /* Для Type 2:
     * data[0] = начало первого интервала (TDB seconds past J2000)
     * data[1] = конец первого интервала
     * data[2] = число коэффициентов (n_coeff)
     * Затем идут n_coeff значений для X, Y, Z
     * Потом следующий интервал
     */

    if (nread >= 3) {
        double interval_start = data[0];
        double interval_end = data[1];
        double interval_length_sec = interval_end - interval_start;
        double interval_length_days = interval_length_sec / 86400.0;

        printf("  Native interval: %.2f days (%.0f seconds)\n",
               interval_length_days, interval_length_sec);

        int n_coeff = (int)data[2];
        printf("  Chebyshev coefficients per component: %d\n", n_coeff);

        /* Вычисляем количество интервалов */
        double total_sec = end - start;
        int estimated_intervals = (int)(total_sec / interval_length_sec);
        printf("  Estimated intervals: %d\n", estimated_intervals);
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <spk_file>\n", argv[0]);
        printf("\nExample:\n");
        printf("  %s data/ephemerides/jpl/de431/de431_part-1.bsp\n", argv[0]);
        return 1;
    }

    const char *spk_file = argv[1];

    printf("\n================================================================================\n");
    printf("Analyzing: %s\n", spk_file);
    printf("================================================================================\n\n");

    /* Загружаем SPK файл */
    SpiceInt handle;
    dafopr_c(spk_file, &handle);

    if (failed_c()) {
        char msg[1024];
        getmsg_c("LONG", 1024, msg);
        printf("Error loading SPK file: %s\n", msg);
        reset_c();
        return 1;
    }

    /* Получаем список всех объектов в файле */
    SPICEINT_CELL(ids, MAXOBJ);
    spkobj_c(spk_file, &ids);

    if (failed_c()) {
        char msg[1024];
        getmsg_c("LONG", 1024, msg);
        printf("Error getting object list: %s\n", msg);
        reset_c();
        dafcls_c(handle);
        return 1;
    }

    int n_bodies = card_c(&ids);
    printf("Found %d bodies in file\n\n", n_bodies);

    /* Анализируем каждое тело */
    for (int i = 0; i < n_bodies; i++) {
        int body_id = SPICE_CELL_ELEM_I(&ids, i);
        const char *body_name = get_body_name(body_id);

        printf("Body %d: %s\n", body_id, body_name);

        /* Получаем временное покрытие */
        SPICEDOUBLE_CELL(cover, MAXIVL);
        spkcov_c(spk_file, body_id, &cover);

        if (failed_c()) {
            printf("  Error getting coverage\n");
            reset_c();
            continue;
        }

        int n_intervals = wncard_c(&cover);
        if (n_intervals == 0) {
            printf("  No coverage\n\n");
            continue;
        }

        /* Берём первый интервал покрытия */
        double start, end;
        wnfetd_c(&cover, 0, &start, &end);

        char start_str[100], end_str[100];
        et2utc_c(start, "C", 0, 100, start_str);
        et2utc_c(end, "C", 0, 100, end_str);

        printf("  Coverage: %s to %s\n", start_str, end_str);
        printf("  Duration: %.2f years\n", (end - start) / 86400.0 / 365.25);

        /* Анализируем сегмент для получения нативного интервала */
        analyze_segment(handle, body_id, start, end);

        printf("\n");
    }

    /* Закрываем файл */
    dafcls_c(handle);

    printf("Analysis complete.\n\n");

    return 0;
}
