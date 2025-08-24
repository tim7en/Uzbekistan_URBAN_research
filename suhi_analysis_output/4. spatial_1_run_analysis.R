# ==========================================================
# Spatial relationships (city × year) — analysis & plots
# Inputs (prefer these if they exist):
#   out/spatial_per_year.csv
#   out/spatial_temporal_changes.csv
# Fallback (if CSVs missing): reads reports/spatial_relationships_report.json
# Outputs (PNG):
#   out/spatial_timeseries_veg_access_ci.png
#   out/spatial_timeseries_built_distance_ci.png
#   out/spatial_bars_2016_vs_2024_built_distance_ci.png
#   out/spatial_change_diverging_veg_patch_count_pct.png
#   out/spatial_change_heatmap_pct.png
#   out/spatial_scatter_built_vs_veg_access.png
# ==========================================================

# ---- Packages ----
pkgs <- c("readr","dplyr","tidyr","purrr","tibble","stringr","ggplot2","forcats","scales")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

dir.create("out", showWarnings = FALSE, recursive = TRUE)

# ---- Load data ----
per_year_csv   <- "out/spatial_per_year.csv"
changes_csv    <- "out/spatial_temporal_changes.csv"
json_fallback  <- "reports/spatial_relationships_report.json"

num_or_na <- function(x) { if (is.null(x)) return(NA_real_); as.numeric(x) }

if (file.exists(per_year_csv) && file.exists(changes_csv)) {
  df_per_year <- readr::read_csv(per_year_csv, show_col_types = FALSE)
  df_changes  <- readr::read_csv(changes_csv,  show_col_types = FALSE)
} else if (file.exists(json_fallback)) {
  # minimal fallback flattener (only the bits needed for plotting)
  raw <- jsonlite::fromJSON(json_fallback, simplifyVector = FALSE)
  
  flatten_city_year <- function(city_name, city_list) {
    yrs <- names(city_list)
    purrr::map_dfr(yrs, function(y) {
      dat <- city_list[[y]]
      bd_ci <- purrr::pluck(dat, "built_distance_stats","city","ci95")
      va_ci <- purrr::pluck(dat, "vegetation_accessibility","city","ci95")
      tibble::tibble(
        city  = city_name,
        year  = as.integer(y),
        veg_patch_count          = num_or_na(purrr::pluck(dat,"veg_patches","patch_count")),
        veg_mean_patch_area_m2   = num_or_na(purrr::pluck(dat,"veg_patches","mean_patch_area_m2")),
        built_patch_count        = num_or_na(purrr::pluck(dat,"built_patches","patch_count")),
        built_mean_distance_m    = num_or_na(purrr::pluck(dat,"built_distance_stats","city","mean")),
        built_distance_ci95_lo   = suppressWarnings(as.numeric(if (is.null(bd_ci)) NA else bd_ci[[1]])),
        built_distance_ci95_hi   = suppressWarnings(as.numeric(if (is.null(bd_ci)) NA else bd_ci[[2]])),
        veg_access_mean_m        = num_or_na(purrr::pluck(dat,"vegetation_accessibility","city","mean")),
        veg_access_ci95_lo       = suppressWarnings(as.numeric(if (is.null(va_ci)) NA else va_ci[[1]])),
        veg_access_ci95_hi       = suppressWarnings(as.numeric(if (is.null(va_ci)) NA else va_ci[[2]]))
      )
    })
  }
  df_per_year <- purrr::imap_dfr(raw$per_year, flatten_city_year)
  
  # compute changes 2016→2024 if not present
  df_changes <- df_per_year %>%
    filter(year %in% c(2016, 2024)) %>%
    select(city, year,
           veg_patch_count, veg_mean_patch_area_m2,
           built_mean_distance_m, veg_access_mean_m) %>%
    pivot_wider(names_from = year, values_from = c(veg_patch_count, veg_mean_patch_area_m2,
                                                   built_mean_distance_m, veg_access_mean_m),
                names_sep = "_") %>%
    mutate(
      veg_patch_count_pct        = 100*(veg_patch_count_2024 - veg_patch_count_2016)/veg_patch_count_2016,
      veg_mean_patch_area_m2_pct = 100*(veg_mean_patch_area_m2_2024 - veg_mean_patch_area_m2_2016)/veg_mean_patch_area_m2_2016,
      built_mean_distance_m_pct  = 100*(built_mean_distance_m_2024 - built_mean_distance_m_2016)/built_mean_distance_m_2016,
      veg_access_mean_m_pct      = 100*(veg_access_mean_m_2024 - veg_access_mean_m_2016)/veg_access_mean_m_2016
    ) %>%
    select(city, ends_with("_pct"))
} else {
  stop("No data found. Supply CSVs in 'out/' or the JSON fallback in 'reports/'.")
}

# basic hygiene
df_per_year <- df_per_year %>%
  mutate(
    city = as.character(city),
    year = as.integer(year)
  )

# shared theme
theme_pub <- function() {
  theme_minimal(base_size = 12) +
    theme(
      panel.grid.minor = element_blank(),
      plot.title = element_text(face = "bold"),
      legend.position = "top"
    )
}

# A palette that works well for many cities
pal_cities <- function(n) scales::hue_pal(l = 55, c = 90)(n)

# ==========================================================
# 1) Time-series with CI ribbons — Vegetation Accessibility
# ==========================================================
p1 <- ggplot(df_per_year,
             aes(x = year, y = veg_access_mean_m, color = city, group = city)) +
  geom_ribbon(aes(ymin = veg_access_ci95_lo, ymax = veg_access_ci95_hi, fill = city),
              alpha = 0.18, color = NA) +
  geom_line(size = 1) +
  scale_color_manual(values = pal_cities(length(unique(df_per_year$city)))) +
  scale_fill_manual(values = pal_cities(length(unique(df_per_year$city)))) +
  labs(title = "Vegetation accessibility (mean distance to vegetation)",
       x = NULL, y = "Meters") +
  theme_pub()
ggsave("out/spatial_timeseries_veg_access_ci.png", p1, width = 11, height = 6, dpi = 150)

# ==========================================================
# 2) Time-series with CI ribbons — Built Distance
# ==========================================================
p2 <- ggplot(df_per_year,
             aes(x = year, y = built_mean_distance_m, color = city, group = city)) +
  geom_ribbon(aes(ymin = built_distance_ci95_lo, ymax = built_distance_ci95_hi, fill = city),
              alpha = 0.18, color = NA) +
  geom_line(size = 1) +
  scale_color_manual(values = pal_cities(length(unique(df_per_year$city)))) +
  scale_fill_manual(values = pal_cities(length(unique(df_per_year$city)))) +
  labs(title = "Built-up proximity (mean distance to built areas)",
       x = NULL, y = "Meters") +
  theme_pub()
ggsave("out/spatial_timeseries_built_distance_ci.png", p2, width = 11, height = 6, dpi = 150)

# ==========================================================
# 3) 2016 vs 2024 comparison — Built Distance (bars + CI)
# ==========================================================
df_2yr <- df_per_year %>% filter(year %in% c(2016, 2024))
pd <- position_dodge(width = 0.8)
p3 <- ggplot(df_2yr,
             aes(x = forcats::fct_reorder(city, built_mean_distance_m),
                 y = built_mean_distance_m, fill = factor(year))) +
  geom_col(position = pd, width = 0.75) +
  geom_errorbar(aes(ymin = built_distance_ci95_lo, ymax = built_distance_ci95_hi),
                position = pd, width = 0.25, linewidth = 0.5) +
  coord_flip() +
  scale_fill_brewer(palette = "Set2", name = "Year") +
  labs(title = "Built-up distance by city: 2016 vs 2024",
       x = NULL, y = "Meters") +
  theme_pub()
ggsave("out/spatial_bars_2016_vs_2024_built_distance_ci.png", p3, width = 9, height = 6, dpi = 150)

# ==========================================================
# 4) Diverging bars — % change in vegetation patch count
# ==========================================================
if ("veg_patch_count_pct" %in% names(df_changes)) {
  p4 <- df_changes %>%
    mutate(city = forcats::fct_reorder(city, veg_patch_count_pct)) %>%
    ggplot(aes(x = city, y = veg_patch_count_pct,
               fill = veg_patch_count_pct > 0)) +
    geom_col(width = 0.7) +
    geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
    coord_flip() +
    scale_fill_manual(values = c("#d73027", "#1a9850"), guide = "none") +
    scale_y_continuous(labels = label_percent(accuracy = 0.1, scale = 1)) +
    labs(title = "Vegetation patch count — % change (2016→2024)",
         x = NULL, y = "% change") +
    theme_pub()
  ggsave("out/spatial_change_diverging_veg_patch_count_pct.png", p4, width = 8, height = 5, dpi = 150)
}

# ==========================================================
# 5) Heatmap — city × indicator (% change 2016→2024)
# ==========================================================
pct_cols <- names(df_changes)[stringr::str_detect(names(df_changes), "_pct$")]
if (length(pct_cols)) {
  hm <- df_changes %>%
    select(city, all_of(pct_cols)) %>%
    pivot_longer(-city, names_to = "indicator", values_to = "pct") %>%
    mutate(indicator = indicator %>%
             str_replace("_pct$", "") %>%
             str_replace_all("_", " ") %>%
             stringr::str_to_sentence())
  
  p5 <- ggplot(hm, aes(x = indicator, y = city, fill = pct)) +
    geom_tile(color = "white", linewidth = 0.3) +
    scale_fill_gradient2(low = "#d73027", mid = "white", high = "#1a9850",
                         midpoint = 0, labels = label_percent(scale = 1)) +
    labs(title = "Percent change by indicator (2016→2024)",
         x = NULL, y = NULL, fill = "% change") +
    theme_pub() +
    theme(axis.text.x = element_text(angle = 30, hjust = 1))
  ggsave("out/spatial_change_heatmap_pct.png", p5, width = 11, height = 6, dpi = 150)
}

# ==========================================================
# 6) Relationship — built distance vs vegetation access
# ==========================================================
p6 <- ggplot(df_per_year,
             aes(x = built_mean_distance_m, y = veg_access_mean_m, color = city)) +
  geom_point(alpha = 0.75, size = 2) +
  geom_smooth(method = "lm", se = FALSE, linewidth = 0.8, show.legend = FALSE) +
  scale_color_manual(values = pal_cities(length(unique(df_per_year$city)))) +
  labs(title = "Relationship: distance to built vs. distance to vegetation",
       x = "Built distance (m)", y = "Vegetation access distance (m)", color = "City") +
  theme_pub()
ggsave("out/spatial_scatter_built_vs_veg_access.png", p6, width = 9, height = 6, dpi = 150)

message("✅ Plots written to 'out/'.")
