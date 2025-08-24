# ===============================
# Urban SUHI / Vegetation / Biomass analysis (2016–2024, 14 cities)
# Chunk-safe version (per-city partials) to avoid elapsed-time limit
# ===============================

# -------- Packages --------
pkgs <- c("jsonlite","ggplot2","dplyr","tidyr","forcats","broom","readr","scales")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# Optional (sharper/faster PNG on Windows)
if (!"ragg" %in% rownames(installed.packages())) install.packages("ragg")
use_ragg <- requireNamespace("ragg", quietly = TRUE)
ggsave2 <- function(filename, plot, width, height, dpi = 200) {
  if (use_ragg) {
    ggplot2::ggsave(filename, plot, width = width, height = height, dpi = dpi,
                    device = ragg::agg_png)
  } else {
    ggplot2::ggsave(filename, plot, width = width, height = height, dpi = dpi)
  }
}

# -------- Safety / options --------
try(setTimeLimit(cpu = Inf, elapsed = Inf, transient = TRUE), silent = TRUE)
options(stringsAsFactors = FALSE)
`%||%` <- function(x, y) if (is.null(x)) y else x
safe_num <- function(x) if (is.null(x)) NA_real_ else suppressWarnings(as.numeric(x))

# -------- Locate your JSON file --------
# Set your preferred path here if needed:
# path_to_json <- "D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/reports/auxiliary_batch_results.json"

if (!exists("path_to_json")) {
  candidates <- c(
    "reports/auxiliary_batch_results.json",      # repo layout
    "auxiliary_batch_results.json",              # same folder
    "D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/reports/auxiliary_batch_results.json"
  )
  path_to_json <- candidates[file.exists(candidates)][1]
}
if (is.na(path_to_json)) stop("JSON not found. Set `path_to_json` to your file path.")
message("Using file: ", path_to_json)

raw <- jsonlite::fromJSON(path_to_json, simplifyVector = FALSE)

# -------- Flattener (robust, fast, no purrr in inner loops) --------
flatten_city_year <- function(city_name, year_key, x) {
  stats <- x$stats %||% list()
  stats_row <- tibble::tibble(
    city  = city_name,
    year  = as.integer(year_key),
    summer_ndvi_mean = safe_num(stats$summer_ndvi_mean),
    winter_ndvi_mean = safe_num(stats$winter_ndvi_mean),
    ndvi_change_mean = safe_num(stats$ndvi_change_mean),
    summer_evi_mean  = safe_num(stats$summer_evi_mean),
    winter_evi_mean  = safe_num(stats$winter_evi_mean),
    evi_change_mean  = safe_num(stats$evi_change_mean),
    summer_lst_mean  = safe_num(stats$summer_lst_mean),
    winter_lst_mean  = safe_num(stats$winter_lst_mean),
    lst_change_mean  = safe_num(stats$lst_change_mean),
    summer_biomass_t_per_ha = safe_num(stats$summer_biomass_t_per_ha),
    winter_biomass_t_per_ha = safe_num(stats$winter_biomass_t_per_ha),
    biomass_change_t_per_ha = safe_num(stats$biomass_change_t_per_ha)
  )
  unc <- x$uncertainty %||% list()
  if (length(unc) == 0L) {
    unc_tbl <- tibble::tibble()
  } else {
    rows <- vector("list", length(unc))
    nms  <- names(unc)
    for (i in seq_along(unc)) {
      ci <- (unc[[i]]$city %||% list())
      ci95 <- ci$ci95 %||% list(NA_real_, NA_real_)
      rows[[i]] <- tibble::tibble(
        city  = city_name,
        year  = as.integer(year_key),
        metric_unc = nms[[i]],        # e.g. "summer_ndvi"
        mean  = safe_num(ci$mean),
        stdDev = safe_num(ci$stdDev),
        count = safe_num(ci$count),
        stdError = safe_num(ci$stdError),
        ci_low = safe_num(ci95[[1]]),
        ci_high = safe_num(ci95[[2]])
      )
    }
    unc_tbl <- dplyr::bind_rows(rows)
  }
  list(stats = stats_row, uncertainty = unc_tbl)
}

# -------- Chunked flatten (per city) to avoid timeouts --------
dir.create("out", showWarnings = FALSE)
dir.create("out/partials", showWarnings = FALSE)

city_names <- names(raw)
for (city_name in city_names) {
  years <- names(raw[[city_name]])
  city_stats <- vector("list", length(years))
  city_unc   <- vector("list", length(years))
  j <- 0L
  for (yk in years) {
    j <- j + 1L
    rec <- flatten_city_year(city_name, yk, raw[[city_name]][[yk]])
    city_stats[[j]] <- rec$stats
    city_unc[[j]]   <- if (nrow(rec$uncertainty)) rec$uncertainty else NULL
  }
  cs <- dplyr::bind_rows(city_stats)
  cu <- dplyr::bind_rows(Filter(Negate(is.null), city_unc))
  readr::write_csv(cs, file.path("out/partials", paste0("stats_", city_name, ".csv")))
  if (nrow(cu)) readr::write_csv(cu, file.path("out/partials", paste0("unc_", city_name, ".csv")))
  rm(cs, cu); gc()
}

# -------- Combine partials --------
stats_files <- list.files("out/partials", pattern = "^stats_.*\\.csv$", full.names = TRUE)
unc_files   <- list.files("out/partials", pattern = "^unc_.*\\.csv$",   full.names = TRUE)

stats_wide <- dplyr::bind_rows(lapply(stats_files, readr::read_csv, show_col_types = FALSE))
unc_long   <- if (length(unc_files)) dplyr::bind_rows(lapply(unc_files, readr::read_csv, show_col_types = FALSE)) else tibble::tibble()

# -------- Tidy/derived indicators --------
stats_long <- tidyr::pivot_longer(
  stats_wide, cols = -c(city, year), names_to = "metric", values_to = "value"
)

metric_labels <- c(
  summer_ndvi_mean = "NDVI (Summer)",
  winter_ndvi_mean = "NDVI (Winter)",
  ndvi_change_mean = "NDVI Δ (Summer–Winter)",
  summer_evi_mean  = "EVI (Summer)",
  winter_evi_mean  = "EVI (Winter)",
  evi_change_mean  = "EVI Δ (Summer–Winter)",
  summer_lst_mean  = "LST (Summer)",
  winter_lst_mean  = "LST (Winter)",
  lst_change_mean  = "LST Δ (Summer–Winter)",
  summer_biomass_t_per_ha = "Biomass t/ha (Summer)",
  winter_biomass_t_per_ha = "Biomass t/ha (Winter)",
  biomass_change_t_per_ha = "Biomass Δ t/ha (Summer–Winter)"
)

# Simple "heat risk proxy": hotter summers + lower greenness
heat_risk <- dplyr::transmute(
  stats_wide, city, year,
  heat_risk_proxy = scales::rescale(summer_lst_mean) - scales::rescale(summer_ndvi_mean)
)

# Map uncertainty metric names -> stats metric names
unc_map <- tibble::tibble(
  metric_unc = c("summer_ndvi","winter_ndvi","ndvi_change",
                 "summer_evi","winter_evi","evi_change",
                 "summer_lst","winter_lst","lst_change"),
  metric = c("summer_ndvi_mean","winter_ndvi_mean","ndvi_change_mean",
             "summer_evi_mean","winter_evi_mean","evi_change_mean",
             "summer_lst_mean","winter_lst_mean","lst_change_mean")
)
unc_joined <- dplyr::left_join(unc_long, unc_map, by = "metric_unc")
stats_with_unc <- dplyr::left_join(stats_long, unc_joined, by = c("city","year","metric"))

# -------- Trend analysis (2016–2024 slope per city) --------
key_trend_metrics <- c("summer_ndvi_mean","summer_lst_mean","summer_biomass_t_per_ha")
trend_results <- stats_long |>
  dplyr::filter(metric %in% key_trend_metrics) |>
  dplyr::group_by(city, metric) |>
  dplyr::filter(!is.na(value)) |>
  dplyr::summarise({
    fit <- lm(value ~ year)
    broom::tidy(fit) |>
      dplyr::filter(term == "year") |>
      dplyr::transmute(slope = estimate, pval = p.value)
  }, .groups = "drop_last") |>
  tidyr::unnest(cols = c(slope, pval)) |>
  dplyr::ungroup() |>
  dplyr::mutate(direction = dplyr::case_when(
    is.na(slope) ~ "N/A",
    slope > 0    ~ "Increasing",
    slope < 0    ~ "Decreasing",
    TRUE         ~ "Flat"
  ))

# -------- Deltas 2016 → 2024 --------
delta_2016_2024 <- stats_long |>
  dplyr::filter(year %in% c(2016, 2024)) |>
  dplyr::group_by(city, metric) |>
  dplyr::summarise(
    v2016 = value[year == 2016][1],
    v2024 = value[year == 2024][1],
    delta = v2024 - v2016,
    .groups = "drop"
  )

# -------- Output folder & CSV exports --------
readr::write_csv(stats_wide, "out/stats_wide.csv")
readr::write_csv(stats_long, "out/stats_long.csv")
readr::write_csv(trend_results, "out/trend_results.csv")
readr::write_csv(delta_2016_2024, "out/delta_2016_2024.csv")
readr::write_csv(heat_risk, "out/heat_risk_proxy.csv")

# -------- PLOTS (meaningful views) --------

# A) Time-series: Summer NDVI & LST (one facet per city)
plot_time_series <- function(metric_key, ylab) {
  stats_long |>
    dplyr::filter(metric == metric_key) |>
    ggplot2::ggplot(ggplot2::aes(year, value, group = city)) +
    ggplot2::geom_line(alpha = 0.8) +
    ggplot2::geom_point(size = 1.1) +
    ggplot2::facet_wrap(~ forcats::fct_reorder(city, value, .fun = mean, .desc = TRUE),
                        scales = "free_y") +
    ggplot2::labs(x = NULL, y = ylab,
                  title = paste0(metric_labels[[metric_key]], " — 2016–2024")) +
    ggplot2::theme_minimal(base_size = 12)
}
p_ndvi <- plot_time_series("summer_ndvi_mean", "NDVI")
p_lst  <- plot_time_series("summer_lst_mean",  "LST (°C)")
ggsave2("out/ts_summer_ndvi_by_city.png", p_ndvi, width = 12, height = 8)
ggsave2("out/ts_summer_lst_by_city.png",  p_lst,  width = 12, height = 8)

# B) Heatmap: Summer LST across cities/years (quick comparative SUHI feel)
p_heat <- stats_long |>
  dplyr::filter(metric == "summer_lst_mean") |>
  dplyr::mutate(city = forcats::fct_reorder(city, value, .fun = mean, .desc = TRUE)) |>
  ggplot2::ggplot(ggplot2::aes(x = factor(year), y = city, fill = value)) +
  ggplot2::geom_tile() +
  ggplot2::scale_fill_viridis_c(option = "A", name = "LST") +
  ggplot2::labs(x = "Year", y = "City", title = "Summer LST Heatmap (2016–2024)") +
  ggplot2::theme_minimal(base_size = 12)
ggsave2("out/heatmap_summer_lst.png", p_heat, width = 10, height = 8)

# C) NDVI vs LST (Summer): shows greenness–heat relationship
p_scatter <- stats_wide |>
  ggplot2::ggplot(ggplot2::aes(summer_ndvi_mean, summer_lst_mean, color = as.factor(year))) +
  ggplot2::geom_point(alpha = 0.75) +
  ggplot2::geom_smooth(method = "lm", se = FALSE) +
  ggplot2::labs(x = "NDVI (Summer)", y = "LST (Summer)", color = "Year",
                title = "Relationship between Summer NDVI and Summer LST") +
  ggplot2::theme_minimal(base_size = 12)
ggsave2("out/scatter_ndvi_vs_lst.png", p_scatter, width = 9, height = 6)

# D) Trends (slopes): warming / greening / biomass change rates
p_trends <- trend_results |>
  dplyr::mutate(metric = dplyr::recode(metric,
                                       summer_ndvi_mean = "NDVI (Summer)",
                                       summer_lst_mean = "LST (Summer)",
                                       summer_biomass_t_per_ha = "Biomass t/ha (Summer)"),
                sig = dplyr::if_else(pval < 0.05, "p < 0.05", "n.s.")) |>
  ggplot2::ggplot(ggplot2::aes(x = reorder(city, slope), y = slope, fill = sig)) +
  ggplot2::geom_col() +
  ggplot2::coord_flip() +
  ggplot2::facet_wrap(~ metric, scales = "free_x") +
  ggplot2::labs(x = NULL, y = "Slope per year",
                title = "2016–2024 Linear Trends by City") +
  ggplot2::theme_minimal(base_size = 12)
ggsave2("out/trends_slopes_by_city.png", p_trends, width = 12, height = 8)

# E) Uncertainty ribbons: Summer NDVI with 95% CI (if available)
p_unc <- stats_with_unc |>
  dplyr::filter(metric == "summer_ndvi_mean") |>
  ggplot2::ggplot(ggplot2::aes(year, value, group = city)) +
  ggplot2::geom_ribbon(ggplot2::aes(ymin = ci_low, ymax = ci_high),
                       alpha = 0.2, na.rm = TRUE) +
  ggplot2::geom_line() +
  ggplot2::facet_wrap(~ city, scales = "free_y") +
  ggplot2::labs(x = NULL, y = "NDVI (Summer)",
                title = "Summer NDVI with 95% CI (if available)") +
  ggplot2::theme_minimal(base_size = 12)
ggsave2("out/summer_ndvi_uncertainty_ribbons.png", p_unc, width = 12, height = 8)

# F) 2016→2024 delta bars for SUHI-like signal (summer LST, LST Δ)
delta_plot <- function(metric_key, title_txt, ylab_txt) {
  delta_2016_2024 |>
    dplyr::filter(metric == metric_key) |>
    ggplot2::ggplot(ggplot2::aes(x = reorder(city, delta), y = delta, fill = delta > 0)) +
    ggplot2::geom_col() +
    ggplot2::coord_flip() +
    ggplot2::scale_fill_manual(values = c("TRUE" = "#a6cee3", "FALSE" = "#fb9a99"), guide = "none") +
    ggplot2::labs(x = NULL, y = ylab_txt, title = title_txt) +
    ggplot2::theme_minimal(base_size = 12)
}
p_delta_lst  <- delta_plot("summer_lst_mean", "Δ Summer LST (2024–2016)", "Δ LST (°C)")
p_delta_suhi <- delta_plot("lst_change_mean", "Δ LST (Summer–Winter) (2024–2016)", "Δ LST Δ (°C)")
ggsave2("out/delta_summer_lst_2016_2024.png",  p_delta_lst,  width = 9, height = 7)
ggsave2("out/delta_lst_change_2016_2024.png",  p_delta_suhi, width = 9, height = 7)

# -------- Topline console summary --------
cat("\n=== TOPLINES ===\n")
cat("Rows in stats_wide: ", nrow(stats_wide), "  Cities: ", length(unique(stats_wide$city)),
    "  Years: ", paste0(min(stats_wide$year, na.rm=TRUE), "–", max(stats_wide$year, na.rm=TRUE)),"\n", sep = "")

cat("\nHottest summers (top 5 city-years):\n")
stats_wide |>
  arrange(desc(summer_lst_mean)) |>
  select(city, year, summer_lst_mean) |>
  slice_head(n = 5) |>
  print()

cat("\nGreenest summers (top 5 city-years by NDVI):\n")
stats_wide |>
  arrange(desc(summer_ndvi_mean)) |>
  select(city, year, summer_ndvi_mean) |>
  slice_head(n = 5) |>
  print()

cat("\nCities with significant trends (p < 0.05):\n")
trend_results |>
  filter(pval < 0.05) |>
  arrange(metric, desc(slope)) |>
  print()

cat("\nCSV summaries and plots saved in the 'out/' folder.\n")
