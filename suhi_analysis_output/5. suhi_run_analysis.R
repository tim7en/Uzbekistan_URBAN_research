# ==============================
# SUHI charts: 2016 vs 2024 (+ dashboard-style chart)
# ==============================

# ---- Packages ----
pkgs <- c("readr","dplyr","tidyr","ggplot2","forcats","stringr","scales")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Input ----
# CSV should have at least: city, year, and either suhi OR (urban_mean & rural_mean)
data_path <- "out/suhi_batch_summary_flat.csv"   # <- change if needed

# ---- Read ----
df_raw <- readr::read_csv(data_path, show_col_types = FALSE)

# ---- Helpers ----
clean_city <- function(x) {
  x %>%
    as.character() %>%
    stringr::str_replace_all("\\u00A0", " ") %>%  # non-breaking space
    stringr::str_squish() %>%
    stringr::str_trim()
}

# ---- Hygiene & fallbacks ----
df <- df_raw %>%
  mutate(
    city = clean_city(city),
    year = as.integer(year),
    # Robust numeric conversion (will coerce char->numeric and keep numeric as is)
    across(any_of(c("urban_mean","rural_mean","suhi")), ~ suppressWarnings(as.numeric(.)))
  )

# If "suhi" absent but we have urban_mean and rural_mean, derive it
if (!"suhi" %in% names(df) && all(c("urban_mean","rural_mean") %in% names(df))) {
  df <- df %>% mutate(suhi = urban_mean - rural_mean)
}

# Keep only what we need going forward
stopifnot(all(c("city","year","suhi") %in% names(df)))

# Average duplicates per (city, year) to prevent double-bars / label drift
df_agg <- df %>%
  group_by(city, year) %>%
  summarise(suhi = mean(suhi, na.rm = TRUE), .groups = "drop")

# ==============================
# Focus on 2016 & 2024
# ==============================
df_2yrs <- df_agg %>%
  filter(year %in% c(2016, 2024))

# Build paired wide table (one row per city that has both years)
paired <- df_2yrs %>%
  select(city, year, suhi) %>%
  pivot_wider(names_from = year, values_from = suhi, names_prefix = "Y") %>%
  filter(!is.na(Y2016) & !is.na(Y2024)) %>%
  mutate(
    abs_change = Y2024 - Y2016,                                   # 2024 - 2016
    rel_change_pct = ifelse(abs(Y2016) < 1e-9, NA_real_,
                            (Y2024 - Y2016) / abs(Y2016) * 100),   # % vs 2016 (safe)
    change_sign = case_when(
      abs_change >  0 ~ "Increase",
      abs_change <  0 ~ "Decrease",
      TRUE            ~ "No change"
    )
  ) %>%
  arrange(rel_change_pct)

if (nrow(paired) == 0) stop("No cities have both 2016 and 2024 SUHI values.")

# Freeze factor order once to keep labels aligned with bars
paired <- paired %>%
  mutate(city_f = factor(city, levels = city))

# ---- Output folder ----
out_dir <- "plots"
if (!dir.exists(out_dir)) dir.create(out_dir)

# ==============================
# 1) Relative change (%) bar chart (2016 → 2024)
# ==============================
p_rel <- ggplot(paired, aes(x = city_f, y = rel_change_pct)) +
  geom_col() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  coord_flip() +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  labs(
    title = "Relative SUHI change (2016 → 2024)",
    subtitle = "Percent change vs 2016 baseline",
    x = "City",
    y = "Change (%)"
  ) +
  theme_minimal(base_size = 12)

ggsave(file.path(out_dir, "01_relative_change_bar_2016_to_2024.png"),
       p_rel, width = 10, height = 7, dpi = 300)

# ==============================
# 2a) Boxplot: SUHI distributions for 2016 vs 2024 (each point = city)
# ==============================
set.seed(42)
p_box_years <- ggplot(df_2yrs, aes(x = factor(year), y = suhi)) +
  geom_boxplot(outlier.shape = NA, width = 0.5) +
  geom_jitter(width = 0.12, height = 0, alpha = 0.65) +
  labs(
    title = "SUHI distributions across cities",
    subtitle = "Side-by-side for 2016 and 2024",
    x = "Year",
    y = "SUHI"
  ) +
  theme_minimal(base_size = 12)

ggsave(file.path(out_dir, "02a_boxplot_suhi_2016_vs_2024.png"),
       p_box_years, width = 8, height = 6, dpi = 300)

# ==============================
# 2b) Boxplot: per-city differences (2024 − 2016)
# ==============================
p_box_diff <- ggplot(paired, aes(x = "Δ SUHI", y = abs_change)) +
  geom_boxplot(width = 0.4) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  geom_jitter(width = 0.08, height = 0, alpha = 0.6) +
  labs(
    title = "Per-city SUHI change",
    subtitle = "Distribution of differences (2024 − 2016)",
    x = "",
    y = "Change in SUHI"
  ) +
  theme_minimal(base_size = 12)

ggsave(file.path(out_dir, "02b_boxplot_suhi_difference_2024_minus_2016.png"),
       p_box_diff, width = 7, height = 6, dpi = 300)

# ==============================
# 3) Colored bar chart: absolute SUHI change by city (2024 − 2016)
# ==============================
paired_change_order <- paired %>% arrange(abs_change) %>%
  mutate(city_f = factor(city, levels = city))

p_change <- ggplot(paired_change_order,
                   aes(x = city_f, y = abs_change, fill = change_sign)) +
  geom_col() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  coord_flip() +
  labs(
    title = "SUHI change across cities (2024 − 2016)",
    x = "City",
    y = "Change in SUHI",
    fill = "Direction"
  ) +
  theme_minimal(base_size = 12)

ggsave(file.path(out_dir, "03_colored_bar_suhi_change_by_city.png"),
       p_change, width = 10, height = 7, dpi = 300)

# ==============================
# Optional: quick summary to console
# ==============================
paired %>%
  arrange(desc(abs_change)) %>%
  select(city, Y2016, Y2024, abs_change, rel_change_pct) %>%
  mutate(rel_change_pct = sprintf("%.1f%%", rel_change_pct)) %>%
  print(n = Inf)

message("Saved the first three figures to: ", normalizePath(out_dir))

# ==============================
# Dashboard-style SUHI change chart (choose any two years)
# ==============================
baseline_year <- 2016   # <- change to 2016 if you want 2016 vs 2024
compare_year  <- 2024

wide_dash <- df_agg %>%
  filter(year %in% c(baseline_year, compare_year)) %>%
  select(city, year, suhi) %>%
  pivot_wider(names_from = year, values_from = suhi)

paired_dash <- wide_dash %>%
  filter(!is.na(.data[[as.character(baseline_year)]]) &
           !is.na(.data[[as.character(compare_year)]])) %>%
  transmute(
    city,
    change = .data[[as.character(compare_year)]] - .data[[as.character(baseline_year)]],
    sign   = case_when(
      change >  0 ~ "Increase",
      change <  0 ~ "Decrease",
      TRUE        ~ "No change"
    ),
    label = sprintf("%+0.3f", change)
  ) %>%
  arrange(change) %>%
  mutate(city_f = factor(city, levels = city))

stopifnot(nrow(paired_dash) > 0)

cols <- c("Increase" = "#F76C6C", "Decrease" = "#2ECC71", "No change" = "#95A5A6")
pad  <- max(abs(paired_dash$change), na.rm = TRUE) * 0.12
paired_dash <- paired_dash %>%
  mutate(ypos = ifelse(change >= 0, change + pad*0.15, change - pad*0.15))

p_dashboard <- ggplot(paired_dash, aes(x = city_f, y = change, fill = sign)) +
  geom_col(width = 0.7) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  geom_text(aes(y = ypos, label = label), size = 3.5) +
  scale_fill_manual(values = cols, guide = "none") +
  scale_y_continuous(expand = expansion(mult = c(0.05, 0.15))) +
  labs(
    title = sprintf("Dashboard Chart 2: SUHI Change Distribution (%d - %d)",
                    compare_year, baseline_year),
    x = "Cities",
    y = "SUHI Change (°C)"
  ) +
  theme_minimal(base_size = 12) +
  theme(axis.text.x = element_text(angle = 30, hjust = 1))

out_file <- sprintf("plots/dashboard_suhi_change_%d_minus_%d.png", compare_year, baseline_year)
ggsave(out_file, p_dashboard, width = 10, height = 6, dpi = 300)
message("Saved dashboard figure: ", normalizePath(out_file))



