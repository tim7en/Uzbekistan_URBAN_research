# ==============================
# Flatten lulc_analysis_summary.json and fill missing data
# ==============================

# ---- Packages ----
pkgs <- c(
  "jsonlite","dplyr","tidyr","purrr","stringr","tibble",
  "forcats","janitor","glue","zoo","readr"
)
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))
options(dplyr.summarise.inform = FALSE, stringsAsFactors = FALSE)

# ---- Config ----
path_to_json <- "reports/lulc_analysis_summary.json"   # adjust if needed
out_dir      <- "out"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# ---- Helpers ----
`%||%` <- function(x, y) if (is.null(x)) y else x

# Linear interpolate + carry ends (per group)
impute_series <- function(x, idx) {
  # x: numeric vector (may contain NA)
  # idx: numeric index (e.g., years)
  if (all(is.na(x))) return(x)
  # approx across available points
  out <- zoo::na.approx(x, x = idx, na.rm = FALSE)
  # carry forward/backward for edges
  out <- zoo::na.locf(out, na.rm = FALSE)
  out <- zoo::na.locf(out, fromLast = TRUE, na.rm = FALSE)
  as.numeric(out)
}

# Safe numeric
num <- function(x) suppressWarnings(as.numeric(x))

# ---- Load JSON ----
j <- jsonlite::fromJSON(path_to_json, simplifyVector = FALSE)

# ---- Flatten to city-year-class long table ----
# The JSON is a list of cities; each has $years, $areas_m2 (per year list of classes),
# $built_up_area_m2 (named list) and optional entropy under areas_m2[[year]]$`_entropy`.
rows <- map(j, function(city_node) {
  city <- city_node$city %||% NA_character_
  years <- city_node$years %||% list()
  # built up (named list)
  built_map <- city_node$built_up_area_m2 %||% list()
  built_df <- tibble(
    city = city,
    year = as.integer(names(built_map)),
    built_up_area_m2 = as.numeric(unlist(built_map))
  )
  
  # areas_m2: list per year -> each is a named list of classes
  # We'll iterate years explicitly to keep missing years
  per_year <- map(years, function(yy) {
    v <- city_node$areas_m2[[as.character(yy)]]
    if (is.null(v)) {
      return(tibble())
    }
    # split out entropy if present
    ent <- v$`_entropy`
    if (!is.null(ent)) v$`_entropy` <- NULL
    
    # classes are the remaining names
    cls_names <- names(v)
    if (is.null(cls_names) || length(cls_names) == 0) {
      return(tibble())
    }
    tb <- map_dfr(cls_names, function(cl) {
      rec <- v[[cl]]
      tibble(
        city = city,
        year = as.integer(yy),
        class = cl,
        pixels     = num(rec$pixels),
        area_m2    = num(rec$area_m2),
        percentage = num(rec$percentage),
        ci_pct_lo  = if (!is.null(rec$ci_percentage)) num(rec$ci_percentage[[1]]) else NA_real_,
        ci_pct_hi  = if (!is.null(rec$ci_percentage)) num(rec$ci_percentage[[2]]) else NA_real_,
        ci_area_lo = if (!is.null(rec$ci_area_m2))   num(rec$ci_area_m2[[1]])   else NA_real_,
        ci_area_hi = if (!is.null(rec$ci_area_m2))   num(rec$ci_area_m2[[2]])   else NA_real_
      )
    })
    # append entropy as separate columns at year level
    if (!is.null(ent)) {
      tb$entropy_nats <- num(ent$nats)
      tb$entropy_bits <- num(ent$bits)
    } else {
      tb$entropy_nats <- NA_real_
      tb$entropy_bits <- NA_real_
    }
    tb
  }) %>% bind_rows()
  
  # If no class rows exist for this city (shouldn't happen), still return built_df
  if (nrow(per_year) == 0) {
    return(list(classes = tibble(), built = built_df))
  }
  
  # Merge built_up area to every row within the same year (for convenience)
  per_year <- per_year %>%
    left_join(built_df, by = c("city","year"))
  
  list(classes = per_year, built = built_df)
})

classes_long <- map_dfr(rows, "classes")
built_only   <- map_dfr(rows, "built") %>% distinct()

# ---- Compute total area per city-year (if possible) ----
totals <- classes_long %>%
  group_by(city, year) %>%
  summarise(total_area_sum_classes = sum(area_m2, na.rm = TRUE),
            have_any_area = any(!is.na(area_m2))) %>%
  ungroup()

# We'll take "best available" total area per city as:
# 1) If a city-year has a non-trivial sum of class areas, use it.
# 2) Else use the median total over available years (per city).
# 3) Then impute remaining gaps by carrying forward/backward.
total_area_city_year <- totals %>%
  group_by(city) %>%
  mutate(
    # 0 if truly none; treat zeros as NA if no classes present
    total_area = ifelse(have_any_area & total_area_sum_classes > 0, total_area_sum_classes, NA_real_)
  ) %>%
  arrange(city, year) %>%
  group_modify(~{
    df <- .x
    # fill with city median if fully missing
    med <- median(df$total_area, na.rm = TRUE)
    if (is.finite(med)) df$total_area[is.na(df$total_area)] <- med
    # still keep interpolation in case of partial miss
    df$total_area <- impute_series(df$total_area, df$year)
    df
  }) %>%
  ungroup() %>%
  select(city, year, total_area)

# ---- Join totals and impute missing percentage/area intelligently ----
classes_long <- classes_long %>%
  left_join(total_area_city_year, by = c("city","year"))

# For each city+class:
# - Impute percentage via linear interpolation + carry ends
# - Impute area_m2 from percentage * total_area when area missing
# - If percentage missing but area present, back out percentage = area/total * 100
# - pixels: interpolate; round at the end
classes_imputed <- classes_long %>%
  group_by(city, class) %>%
  arrange(city, class, year) %>%
  mutate(
    # First pass: derive percentage if missing but area & total present
    percentage = ifelse(is.na(percentage) & !is.na(area_m2) & !is.na(total_area) & total_area > 0,
                        (area_m2 / total_area) * 100, percentage),
    # Interpolate percentage across years
    percentage = impute_series(percentage, year),
    # Second pass: derive area if missing now that pct + total exist
    area_m2 = ifelse(is.na(area_m2) & !is.na(percentage) & !is.na(total_area),
                     pmax(0, percentage/100 * total_area), area_m2),
    # Interpolate area (in case pct was all missing for some class and total insufficient)
    area_m2 = impute_series(area_m2, year),
    # Pixels: interpolate then round (safe if not used downstream)
    pixels = round(impute_series(pixels, year)),
    # CIs: optional light-touch impute (linear)
    ci_pct_lo  = impute_series(ci_pct_lo, year),
    ci_pct_hi  = impute_series(ci_pct_hi, year),
    ci_area_lo = impute_series(ci_area_lo, year),
    ci_area_hi = impute_series(ci_area_hi, year),
    # Entropy duplicates per year across classes; keep but impute
    entropy_nats = impute_series(entropy_nats, year),
    entropy_bits = impute_series(entropy_bits, year),
    built_up_area_m2 = impute_series(built_up_area_m2, year)
  ) %>%
  ungroup()

# ---- Clean class names and order ----
classes_imputed <- classes_imputed %>%
  mutate(
    class = str_replace_all(class, "_", " "),
    class = fct_relevel(class,
                        "Built Area","Crops","Trees","Rangeland","Bare Ground","Water","Flooded Vegetation","Clouds",
                        after = 0
    )
  ) %>%
  arrange(city, year, class)

# ---- Wide summary (percentages per class + built_up & entropy) ----
city_year_wide <- classes_imputed %>%
  select(city, year, class, percentage, area_m2, built_up_area_m2, entropy_nats, entropy_bits, total_area) %>%
  group_by(city, year) %>%
  mutate(
    # If multiple rows per class (shouldn't), keep latest by order
    rn = row_number()
  ) %>%
  ungroup() %>%
  select(-rn) %>%
  distinct() %>%
  # pivot WIDE on percentage and on area_m2 (suffixes)
  pivot_wider(
    names_from = class,
    values_from = c(percentage, area_m2),
    names_glue = "{.value}__{class}"
  ) %>%
  arrange(city, year)

# ---- Sanity checks ----
# Sum of class percentages may not equal exactly 100 due to rounding/model differences.
city_year_wide <- city_year_wide %>%
  mutate(
    pct_sum_known = rowSums(select(., starts_with("percentage__")), na.rm = TRUE)
  )

# ---- Write outputs ----
write_csv(classes_imputed, file.path(out_dir, "lulc_city_year_class_long_imputed.csv"))
write_csv(city_year_wide, file.path(out_dir, "lulc_city_year_summary_wide_imputed.csv"))

message("Done. Files written to: ", normalizePath(out_dir))
