# ==========================================================
# LULC Analysis & Plot Generator
# Dataset: <your LULC csv> (long format: city, year, class, percentage, area_m2, etc.)
# Outputs: all files prefixed with "lulc_"
# Usage (examples):
#   Rscript generate_lulc_plots.R --csv out/lulc_results.csv --out out
#   Rscript generate_lulc_plots.R --csv out/lulc_results.csv --out out --cities "Andijan,Bukhara"
# ==========================================================

# -------- Packages --------
pkgs <- c(
  "readr","dplyr","tidyr","ggplot2","forcats","scales","stringr","broom"
)
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# -------- CLI Args --------
args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(flag, default = NULL) {
  i <- which(args == flag)
  if (length(i) == 0 || i == length(args)) return(default)
  args[i + 1]
}

csv_path   <- get_arg("--csv", "out/lulc_city_year_class_long_imputed.csv")
out_dir    <- get_arg("--out", "out")
cities_arg <- get_arg("--cities", NA_character_)

if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

# -------- Helpers --------
slug <- function(x) {
  x |>
    str_trim() |>
    str_to_lower() |>
    str_replace_all("[^a-z0-9]+", "_") |>
    str_replace_all("^_|_$", "")
}

# -------- Load data --------
df <- readr::read_csv(csv_path, show_col_types = FALSE)

# Normalize column names (case-insensitive tolerance)
names(df) <- tolower(names(df))
rename_if_exists <- function(.data, old, new) {
  if (old %in% names(.data)) dplyr::rename(.data, !!new := !!sym(old)) else .data
}

df <- df |>
  rename_if_exists("built_up_area_m2", "built_up_area_m2") |>
  rename_if_exists("total_area", "total_area") |>
  rename_if_exists("percentage", "percentage") |>
  rename_if_exists("area_m2", "area_m2") |>
  rename_if_exists("entropy_nats", "entropy_nats") |>
  rename_if_exists("entropy_bits", "entropy_bits")

# Basic checks/conversions
req_cols <- c("city","year","class","percentage")
missing_cols <- setdiff(req_cols, names(df))
if (length(missing_cols)) {
  stop("Missing required columns: ", paste(missing_cols, collapse = ", "))
}
df <- df |>
  mutate(
    year = as.integer(year),
    city = as.character(city),
    class = as.character(class)
  )

# Optional city filter
if (!is.na(cities_arg)) {
  keep <- str_split(cities_arg, ",", simplify = TRUE)
  keep <- trimws(keep[keep != ""])
  df <- df |> filter(city %in% keep)
  message("Filtering to cities: ", paste(unique(keep), collapse = ", "))
}

# -------- Aggregates (helpful CSVs) --------
# Wide table of % by class
wide_pct <- df |>
  select(city, year, class, percentage) |>
  mutate(class = slug(class)) |>
  distinct() |>
  tidyr::pivot_wider(names_from = class, values_from = percentage)

readr::write_csv(wide_pct, file.path(out_dir, "lulc_city_year_percentage_wide.csv"))

# Entropy summary by city-year
entropy_summary <- df |>
  distinct(city, year, .keep_all = TRUE) |>
  select(city, year, starts_with("entropy"), total_area, built_up_area_m2)

readr::write_csv(entropy_summary, file.path(out_dir, "lulc_entropy_summary.csv"))

# Built-up percentage (if built_up_area_m2 + total_area exist)
if (all(c("built_up_area_m2", "total_area") %in% names(df))) {
  builtup_city_year <- df |>
    group_by(city, year) |>
    summarise(
      built_up_area_m2 = dplyr::first(na.omit(built_up_area_m2)),
      total_area       = dplyr::first(na.omit(total_area)),
      .groups = "drop"
    ) |>
    mutate(built_up_pct = 100 * built_up_area_m2 / total_area)
  readr::write_csv(builtup_city_year, file.path(out_dir, "lulc_builtup_timeseries.csv"))
}

# -------- Plotting Themes --------
theme_base <- theme_minimal(base_size = 12) +
  theme(
    legend.position = "bottom",
    plot.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

# -------- Plot Functions (saved with lulc_* prefix) --------
plot_class_pct_lines <- function(d, city) {
  ggplot(d, aes(year, percentage, color = class)) +
    geom_line(linewidth = 1) +
    geom_point(size = 2) +
    scale_y_continuous(labels = label_percent(accuracy = 0.1, scale = 1)) +
    labs(title = paste0("LULC class percentage over time — ", city),
         x = "Year", y = "Percentage (%)", color = "Class") +
    theme_base
}

plot_composition_stacked <- function(d, city) {
  ggplot(d, aes(year, percentage, fill = fct_reorder(class, percentage, .fun = mean, .desc = TRUE))) +
    geom_area(position = "stack", color = NA, alpha = 0.9) +
    scale_y_continuous(labels = label_percent(accuracy = 1, scale = 1), limits = c(0, 100)) +
    labs(title = paste0("LULC composition (stacked %) — ", city),
         x = "Year", y = "Share of area (%)", fill = "Class") +
    theme_base
}

plot_entropy <- function(ent, city) {
  long <- ent |>
    select(year, entropy_nats, entropy_bits) |>
    pivot_longer(cols = starts_with("entropy"),
                 names_to = "metric", values_to = "value")
  ggplot(long, aes(year, value, color = metric)) +
    geom_line(linewidth = 1) + geom_point(size = 2) +
    labs(title = paste0("Landscape entropy over time — ", city),
         x = "Year", y = "Entropy", color = "Metric") +
    theme_base
}

plot_breakdown_bar <- function(d, city, yr) {
  ggplot(filter(d, year == yr),
         aes(x = fct_reorder(class, percentage), y = percentage, fill = class)) +
    geom_col() +
    coord_flip() +
    scale_y_continuous(labels = label_percent(accuracy = 0.1, scale = 1)) +
    labs(title = paste0("LULC breakdown — ", city, " (", yr, ")"),
         x = "Class", y = "Percentage (%)", fill = "Class") +
    theme_base + theme(legend.position = "none")
}

plot_builtup <- function(bu, city) {
  ggplot(bu, aes(year, built_up_pct)) +
    geom_line(linewidth = 1, color = "steelblue") +
    geom_point(size = 2, color = "steelblue") +
    scale_y_continuous(labels = label_percent(accuracy = 0.1, scale = 1)) +
    labs(title = paste0("Built-up share of total area — ", city),
         x = "Year", y = "Built-up (%)") +
  theme_base
}

# -------- Generate Plots per City --------
cities <- sort(unique(df$city))

for (ct in cities) {
  d_city <- df |> filter(city == ct) |>
    mutate(class = forcats::fct_reorder(class, percentage, .fun = mean, .desc = TRUE))
  
  yrs <- sort(unique(d_city$year))
  if (length(yrs) == 0) next
  
  # 1) Lines by class (%)
  f1 <- plot_class_pct_lines(d_city, ct)
  ggsave(
    filename = file.path(out_dir, paste0("lulc_", slug(ct), "_class_percentage_by_year.png")),
    plot = f1, width = 11, height = 6, dpi = 300
  )
  
  # 2) Stacked composition (%)
  f2 <- plot_composition_stacked(d_city, ct)
  ggsave(
    filename = file.path(out_dir, paste0("lulc_", slug(ct), "_composition_stacked_percentage.png")),
    plot = f2, width = 11, height = 6, dpi = 300
  )
  
  # 3) Entropy (if available)
  ent_city <- d_city |>
    distinct(year, .keep_all = TRUE) |>
    select(year, entropy_nats, entropy_bits) |>
    mutate(any_entropy = ifelse(rowSums(is.na(across(everything()))) < 2, TRUE, FALSE))
  if ("entropy_nats" %in% names(ent_city) || "entropy_bits" %in% names(ent_city)) {
    f3 <- plot_entropy(ent_city, ct)
    ggsave(
      filename = file.path(out_dir, paste0("lulc_", slug(ct), "_entropy_over_time.png")),
      plot = f3, width = 11, height = 6, dpi = 300
    )
  }
  
  # 4) Year breakdowns (first & last)
  fyear <- min(yrs); lyear <- max(yrs)
  f4a <- plot_breakdown_bar(d_city, ct, fyear)
  f4b <- plot_breakdown_bar(d_city, ct, lyear)
  ggsave(
    filename = file.path(out_dir, paste0("lulc_", slug(ct), "_", fyear, "_breakdown_bar.png")),
    plot = f4a, width = 8, height = 6, dpi = 300
  )
  ggsave(
    filename = file.path(out_dir, paste0("lulc_", slug(ct), "_", lyear, "_breakdown_bar.png")),
    plot = f4b, width = 8, height = 6, dpi = 300
  )
  
  # 5) Built-up share vs time (if data available)
  if (all(c("built_up_area_m2", "total_area") %in% names(df))) {
    bu_city <- df |>
      filter(city == ct) |>
      distinct(year, .keep_all = TRUE) |>
      transmute(
        year,
        built_up_area_m2 = dplyr::first(na.omit(built_up_area_m2)),
        total_area       = dplyr::first(na.omit(total_area)),
        built_up_pct     = 100 * built_up_area_m2 / total_area
      ) |>
      arrange(year)
    if (nrow(bu_city) > 0 && all(is.finite(bu_city$built_up_pct))) {
      f5 <- plot_builtup(bu_city, ct)
      ggsave(
        filename = file.path(out_dir, paste0("lulc_", slug(ct), "_builtup_share_over_time.png")),
        plot = f5, width = 10, height = 6, dpi = 300
      )
    }
  }
}

# -------- Optional: simple trends for each class (%) by city --------
# (Linear regression: percentage ~ year, per city & class)
trend_tbl <- df |>
  group_by(city, class) |>
  do({
    fit <- try(lm(percentage ~ year, data = .), silent = TRUE)
    if (inherits(fit, "try-error")) return(tibble(term = NA, estimate = NA, p.value = NA))
    broom::tidy(fit)
  }) |>
  ungroup()

readr::write_csv(trend_tbl, file.path(out_dir, "lulc_percentage_trends_by_city_class.csv"))



# ==========================================================
# Plotly chart: Built-up area (2016 vs 2024) by city
# ==========================================================
# LULC: Built-up area by city (2016 vs 2024) — ggplot2
# Requires: dplyr, ggplot2, readr, scales, forcats
# Assumes your long df has columns: city, year, class, area_m2
# and that built-up area is the row where class == "Built Area"
# ==========================================================

# ---- packages (safe re-load) ----
pkgs <- c("dplyr","ggplot2","scales","forcats")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- output dir ----
out_dir <- "out"
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

# ---- derive built-up area for 2016 & 2024 ----
df_builtup <- df %>%
  filter(year %in% c(2016, 2024), class == "Built Area") %>%
  group_by(city, year) %>%
  summarise(built_up_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop")

# Order cities by 2024 to make the chart easier to read
city_order <- df_builtup %>%
  filter(year == 2024) %>%
  arrange(desc(built_up_m2)) %>%
  pull(city)

df_builtup <- df_builtup %>%
  mutate(
    city = factor(city, levels = city_order),
    year = factor(year)
  )
# ---- pretty, grouped bars (fixed for new scales version) ----
p_lulc_builtup <- ggplot(df_builtup,
                         aes(x = city, y = built_up_m2, fill = year)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.6) +
  scale_y_continuous(labels = label_number(scale_cut = cut_si("m"))) +
  scale_fill_manual(values = c("2016" = "#4477AA", "2024" = "#EE6677"),
                    name = "Year") +
  labs(
    title = "Built-up Area by City (2016 vs 2024)",
    subtitle = "LULC — total built-up area (m²)",
    x = NULL, y = "Built-up area (m²)"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    axis.text.x = element_text(angle = 35, hjust = 1, vjust = 1),
    legend.position = "top",
    panel.grid.minor = element_blank()
  )

# ---- save outputs ----
ggsave(file.path(out_dir, "lulc_builtup_area_2016_vs_2024.png"),
       plot = p_lulc_builtup, width = 11, height = 6, dpi = 300)

ggsave(file.path(out_dir, "lulc_builtup_area_2016_vs_2024.pdf"),
       plot = p_lulc_builtup, width = 11, height = 6)



# Helper: extract built-up totals by city & year
get_builtup_by_city_year <- function(dat) {
  if ("built_up_area_m2" %in% names(dat)) {
    dat %>%
      distinct(city, year, built_up_area_m2) %>%
      rename(built_up_m2 = built_up_area_m2)
  } else {
    dat %>%
      filter(tolower(class) %in% c("built area","builtarea","built-up","builtup","urban")) %>%
      group_by(city, year) %>%
      summarise(built_up_m2 = sum(area_m2, na.rm = TRUE), .groups = "drop")
  }
}

built_by_cy <- get_builtup_by_city_year(df)

# Compute absolute and percent growth for 2016 → 2024
built_growth <- built_by_cy %>%
  filter(year %in% c(2016, 2024)) %>%
  tidyr::pivot_wider(names_from = year, values_from = built_up_m2, names_prefix = "y_") %>%
  mutate(
    abs_growth_m2 = y_2024 - y_2016,
    pct_growth = dplyr::if_else(y_2016 > 0, (abs_growth_m2 / y_2016) * 100, NA_real_)
  ) %>%
  arrange(desc(pct_growth))

# Save table
out_dir <- "out"
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
readr::write_csv(built_growth, file.path(out_dir, "lulc_builtup_growth_2016_2024.csv"))

# ---------------- Plots ----------------
library(ggplot2)
library(scales)
library(forcats)

# 1) Percent growth by city (2016→2024)
p_pct <- ggplot(
  built_growth,
  aes(x = fct_reorder(city, pct_growth, .desc = TRUE),
      y = pct_growth, fill = pct_growth)
) +
  geom_col(width = 0.65) +
  coord_flip() +
  scale_y_continuous(labels = label_percent(scale = 1, accuracy = 0.1)) +
  scale_fill_gradient(low = "#4477AA", high = "#EE6677", guide = "none") +
  labs(
    title = "Urban Built-up Growth Rate by City (2016 → 2024)",
    subtitle = "LULC — percent growth relative to 2016",
    x = NULL, y = "Growth rate (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

ggsave(file.path(out_dir, "lulc_builtup_growth_rate_2016_2024.png"),
       plot = p_pct, width = 10, height = 7, dpi = 300)
ggsave(file.path(out_dir, "lulc_builtup_growth_rate_2016_2024.pdf"),
       plot = p_pct, width = 10, height = 7)

# 2) Absolute growth (m²) by city (optional but handy)
p_abs <- ggplot(
  built_growth,
  aes(x = fct_reorder(city, abs_growth_m2, .desc = TRUE),
      y = abs_growth_m2, fill = abs_growth_m2)
) +
  geom_col(width = 0.65) +
  coord_flip() +
  scale_y_continuous(labels = label_number(scale_cut = cut_si("m"))) +
  scale_fill_gradient(low = "#77AADD", high = "#CC6677", guide = "none") +
  labs(
    title = "Urban Built-up Area Change by City (2016 → 2024)",
    subtitle = "LULC — absolute change in built-up area (m²)",
    x = NULL, y = "Change (m²)"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    panel.grid.minor = element_blank()
  )

ggsave(file.path(out_dir, "lulc_builtup_absolute_change_2016_2024.png"),
       plot = p_abs, width = 10, height = 7, dpi = 300)
ggsave(file.path(out_dir, "lulc_builtup_absolute_change_2016_2024.pdf"),
       plot = p_abs, width = 10, height = 7)



#############OTHER landcover changes######

library(dplyr)
library(tidyr)
library(readr)

# Summarise (get average percentage + total area per class)
lulc_changes <- df %>%
  filter(year %in% c(2016, 2024)) %>%
  group_by(city, class, year) %>%
  summarise(
    pct = mean(percentage, na.rm = TRUE),
    area_m2 = sum(area_m2, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  # pivot with names including metric and year
  pivot_wider(
    names_from = year,
    values_from = c(pct, area_m2),
    names_sep = "_"
  ) %>%
  mutate(
    pct_change       = pct_2024 - pct_2016,
    area_change_m2   = area_m2_2024 - area_m2_2016
  )

# Save results
out_dir <- "out"
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
write_csv(lulc_changes, file.path(out_dir, "lulc_class_changes_2016_2024.csv"))


#bar
library(ggplot2)
library(forcats)

p_class_change <- ggplot(lulc_changes,
                         aes(x = fct_reorder(city, pct_change, .fun = sum, .desc = TRUE),
                             y = pct_change, fill = class)) +
  geom_col(position = "stack") +
  coord_flip() +
  scale_y_continuous(labels = scales::label_percent(scale = 1, accuracy = 0.1)) +
  labs(
    title = "LULC Class Changes (2016 → 2024) by City",
    subtitle = "Stacked percentage-point changes (positive = growth, negative = decline)",
    x = NULL, y = "Change in share (%)"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    legend.position = "bottom"
  )

ggsave(file.path(out_dir, "lulc_class_change_stacked_by_city.png"),
       plot = p_class_change, width = 11, height = 7, dpi = 300)



#by classes

p_class_facets <- ggplot(lulc_changes,
                         aes(x = fct_reorder(city, pct_change), y = pct_change, fill = pct_change > 0)) +
  geom_col(width = 0.6) +
  coord_flip() +
  facet_wrap(~ class, scales = "free_y") +
  scale_fill_manual(values = c("TRUE" = "#1b9e77", "FALSE" = "#d95f02"),
                    labels = c("Loss","Gain")) +
  scale_y_continuous(labels = scales::label_percent(scale = 1, accuracy = 0.1)) +
  labs(
    title = "LULC Class Changes 2016 → 2024 by City",
    subtitle = "Percentage-point change per class",
    x = NULL, y = "Change (%)", fill = "Change"
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold"),
    legend.position = "bottom"
  )

ggsave(file.path(out_dir, "lulc_class_changes_faceted.png"),
       plot = p_class_facets, width = 12, height = 8, dpi = 300)



message("Saved: out/lulc_builtup_area_2016_vs_2024.(png|pdf)")




message("Done. Plots and tables saved to: ", normalizePath(out_dir))
