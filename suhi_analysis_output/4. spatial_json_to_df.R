# ==========================================================
# Flatten spatial_relationships_report.json → tidy CSVs
#   - out/spatial_per_year.csv           (city-year metrics w/ CIs)
#   - out/spatial_temporal_changes.csv   (city-level deltas)
# Plus: example bar chart of veg_patch_count % change
# ==========================================================

# ---- Packages ----
pkgs <- c("jsonlite","dplyr","tidyr","purrr","tibble","readr","stringr","ggplot2","forcats","rlang")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- I/O setup ----
dir.create("out", showWarnings = FALSE, recursive = TRUE)
path <- "reports/spatial_relationships_report.json"
if (!file.exists(path)) path <- "spatial_relationships_report.json"

# ---- Load JSON ----
raw <- jsonlite::fromJSON(path, simplifyVector = FALSE)

# ---- Helpers (robust to NULLs/lists) ----
num_or_na <- function(x) {
  if (is.null(x)) return(NA_real_)
  if (is.list(x)) x <- unlist(x, recursive = TRUE, use.names = FALSE)
  if (!length(x)) return(NA_real_)
  suppressWarnings(as.numeric(x[1]))
}
pluck_num <- function(.x, ...) num_or_na(purrr::pluck(.x, ..., .default = NA_real_))

# ---- Flatten per_year (NOTE: imap_dfr passes (element, name)) ----
df_per_year <- purrr::imap_dfr(
  raw$per_year,
  function(city_list, city_name) {
    yrs <- names(city_list)
    purrr::map_dfr(yrs, function(y) {
      dat <- city_list[[y]]
      tibble(
        city   = as.character(city_name),
        year   = as.integer(y),
        scale  = pluck_num(dat, "scale"),
        
        veg_patch_count            = pluck_num(dat, "veg_patches","patch_count"),
        veg_mean_patch_area_m2     = pluck_num(dat, "veg_patches","mean_patch_area_m2"),
        veg_median_patch_area_m2   = pluck_num(dat, "veg_patches","median_patch_area_m2"),
        
        built_patch_count          = pluck_num(dat, "built_patches","patch_count"),
        built_mean_patch_area_m2   = pluck_num(dat, "built_patches","mean_patch_area_m2"),
        built_median_patch_area_m2 = pluck_num(dat, "built_patches","median_patch_area_m2"),
        
        built_mean_distance_m      = pluck_num(dat, "built_distance_stats","city","mean"),
        built_distance_stdDev      = pluck_num(dat, "built_distance_stats","city","stdDev"),
        built_distance_count       = pluck_num(dat, "built_distance_stats","city","count"),
        built_distance_ci95_lo     = pluck_num(dat, "built_distance_stats","city","ci95", 1),
        built_distance_ci95_hi     = pluck_num(dat, "built_distance_stats","city","ci95", 2),
        
        veg_access_mean_m          = pluck_num(dat, "vegetation_accessibility","city","mean"),
        veg_access_stdDev          = pluck_num(dat, "vegetation_accessibility","city","stdDev"),
        veg_access_count           = pluck_num(dat, "vegetation_accessibility","city","count"),
        veg_access_ci95_lo         = pluck_num(dat, "vegetation_accessibility","city","ci95", 1),
        veg_access_ci95_hi         = pluck_num(dat, "vegetation_accessibility","city","ci95", 2),
        
        edge_density_m_per_km2     = pluck_num(dat, "edge_density_m_per_km2"),
        veg_patch_isolation_mean_m = pluck_num(dat, "veg_patch_isolation_mean_m")
      )
    })
  }
)

readr::write_csv(df_per_year, "out/spatial_per_year.csv")

# ---- Flatten temporal_changes (correct imap order + force numerics) ----
df_changes <- purrr::imap_dfr(
  raw$temporal_changes,
  function(lst, city_name) {
    vals <- purrr::map(lst, function(x) {
      if (is.null(x)) return(NA_real_)
      if (is.list(x)) x <- unlist(x, recursive = TRUE, use.names = FALSE)
      suppressWarnings(as.numeric(x[1]))
    })
    tibble(city = as.character(city_name), !!!rlang::set_names(vals, names(lst)))
  }
) %>% mutate(across(-city, as.numeric))

readr::write_csv(df_changes, "out/spatial_temporal_changes.csv")

# ---- Example plot: % change in vegetation patch count by city (2016→2024) ----
if (nrow(df_changes)) {
  p <- df_changes %>%
    mutate(city = forcats::fct_reorder(city, veg_patch_count_pct)) %>%
    ggplot(aes(x = city, y = veg_patch_count_pct, fill = veg_patch_count_pct > 0)) +
    geom_col(width = 0.7) +
    geom_hline(yintercept = 0, linewidth = 0.6) +
    coord_flip() +
    scale_y_continuous(labels = scales::label_percent(accuracy = 0.1, scale = 1)) +
    scale_fill_manual(values = c("#d73027","#1a9850"), guide = "none") +
    labs(
      title = "Vegetation Patch Count: % Change (2016 → 2024)",
      x = NULL, y = "% change"
    ) +
    theme_minimal(base_size = 12)
  
  ggsave("out/veg_patch_count_pct_change_bar.png", p, width = 8, height = 5, dpi = 150)
  message("✅ Wrote: out/spatial_per_year.csv, out/spatial_temporal_changes.csv, out/veg_patch_count_pct_change_bar.png")
} else {
  message("⚠️ temporal_changes is empty; wrote per-year CSV only.")
}
