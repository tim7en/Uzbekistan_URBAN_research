# ==============================
# Convert auxiliary_batch_results.json → dataframe (robust, new JSON ok)
# ==============================

# ---- Packages ----
pkgs <- c("jsonlite","dplyr","tibble","tidyr")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Safety / options ----
try(setTimeLimit(cpu = Inf, elapsed = Inf, transient = TRUE), silent = TRUE)
options(stringsAsFactors = FALSE)

# ---- Helpers ----
`%||%` <- function(x, y) if (is.null(x)) y else x
safe_num <- function(x) if (is.null(x)) NA_real_ else suppressWarnings(as.numeric(x))
safe_chr <- function(x) if (is.null(x)) NA_character_ else as.character(x)

# Pull uncertainty safely for a metric path like x$uncertainty$summer_lst$city
get_unc_row <- function(u_metric) {
  if (is.null(u_metric) || is.null(u_metric$city)) {
    return(list(
      count = NA_real_, stdDev = NA_real_, stdError = NA_real_,
      ci95_lo = NA_real_, ci95_hi = NA_real_
    ))
  }
  ci <- u_metric$city$ci95 %||% c(NA_real_, NA_real_)
  list(
    count    = safe_num(u_metric$city$count),
    stdDev   = safe_num(u_metric$city$stdDev),
    stdError = safe_num(u_metric$city$stdError),
    ci95_lo  = safe_num(ci[[1]]),
    ci95_hi  = safe_num(ci[[2]])
  )
}

# ---- Locate & load JSON ----
if (!exists("path_to_json")) {
  candidates <- c(
    "reports/auxiliary_batch_results.json",
    "auxiliary_batch_results.json",
    "D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/reports/auxiliary_batch_results.json"
  )
  hit <- candidates[file.exists(candidates)]
  path_to_json <- if (length(hit)) hit[1] else NA_character_
}
if (is.na(path_to_json)) stop("JSON not found. Set `path_to_json` to your file path.")
message("Using file: ", path_to_json)

raw <- jsonlite::fromJSON(path_to_json, simplifyVector = FALSE)

# ---- Flatten one city-year ----
flatten_city_year <- function(city_name, year_key, x) {
  s  <- x$stats %||% list()
  g  <- x$generated %||% list()
  u  <- x$uncertainty %||% list()

  # uncertainty blocks for each metric we care about (extend as needed)
  u_s_ndvi <- get_unc_row(u$summer_ndvi)
  u_w_ndvi <- get_unc_row(u$winter_ndvi)
  u_d_ndvi <- get_unc_row(u$ndvi_change)

  u_s_evi  <- get_unc_row(u$summer_evi)
  u_w_evi  <- get_unc_row(u$winter_evi)
  u_d_evi  <- get_unc_row(u$evi_change)

  u_s_lst  <- get_unc_row(u$summer_lst)
  u_w_lst  <- get_unc_row(u$winter_lst)
  u_d_lst  <- get_unc_row(u$lst_change)

  tibble::tibble(
    city  = city_name,
    year  = as.integer(year_key),

    # ---- core stats (backward compatible) ----
    summer_ndvi_mean = safe_num(s$summer_ndvi_mean),
    winter_ndvi_mean = safe_num(s$winter_ndvi_mean),
    ndvi_change_mean = safe_num(s$ndvi_change_mean),

    summer_evi_mean  = safe_num(s$summer_evi_mean),
    winter_evi_mean  = safe_num(s$winter_evi_mean),
    evi_change_mean  = safe_num(s$evi_change_mean),

    summer_lst_mean  = safe_num(s$summer_lst_mean),
    winter_lst_mean  = safe_num(s$winter_lst_mean),
    lst_change_mean  = safe_num(s$lst_change_mean),

    summer_biomass_t_per_ha = safe_num(s$summer_biomass_t_per_ha),
    winter_biomass_t_per_ha = safe_num(s$winter_biomass_t_per_ha),
    biomass_change_t_per_ha = safe_num(s$biomass_change_t_per_ha),

    # ---- generated file paths (optional) ----
    summer_veg_tif = safe_chr(g$summer_veg_tif),
    winter_veg_tif = safe_chr(g$winter_veg_tif),
    ndvi_change_tif = safe_chr(g$ndvi_change_tif),
    evi_change_tif  = safe_chr(g$evi_change_tif),
    summer_lst_tif  = safe_chr(g$summer_lst_tif),
    winter_lst_tif  = safe_chr(g$winter_lst_tif),
    lst_change_tif  = safe_chr(g$lst_change_tif),

    # ---- uncertainty: NDVI ----
    summer_ndvi_count   = u_s_ndvi$count,
    summer_ndvi_stddev  = u_s_ndvi$stdDev,
    summer_ndvi_stderr  = u_s_ndvi$stdError,
    summer_ndvi_ci95_lo = u_s_ndvi$ci95_lo,
    summer_ndvi_ci95_hi = u_s_ndvi$ci95_hi,

    winter_ndvi_count   = u_w_ndvi$count,
    winter_ndvi_stddev  = u_w_ndvi$stdDev,
    winter_ndvi_stderr  = u_w_ndvi$stdError,
    winter_ndvi_ci95_lo = u_w_ndvi$ci95_lo,
    winter_ndvi_ci95_hi = u_w_ndvi$ci95_hi,

    ndvi_change_count   = u_d_ndvi$count,
    ndvi_change_stddev  = u_d_ndvi$stdDev,
    ndvi_change_stderr  = u_d_ndvi$stdError,
    ndvi_change_ci95_lo = u_d_ndvi$ci95_lo,
    ndvi_change_ci95_hi = u_d_ndvi$ci95_hi,

    # ---- uncertainty: EVI ----
    summer_evi_count   = u_s_evi$count,
    summer_evi_stddev  = u_s_evi$stdDev,
    summer_evi_stderr  = u_s_evi$stdError,
    summer_evi_ci95_lo = u_s_evi$ci95_lo,
    summer_evi_ci95_hi = u_s_evi$ci95_hi,

    winter_evi_count   = u_w_evi$count,
    winter_evi_stddev  = u_w_evi$stdDev,
    winter_evi_stderr  = u_w_evi$stdError,
    winter_evi_ci95_lo = u_w_evi$ci95_lo,
    winter_evi_ci95_hi = u_w_evi$ci95_hi,

    evi_change_count   = u_d_evi$count,
    evi_change_stddev  = u_d_evi$stdDev,
    evi_change_stderr  = u_d_evi$stdError,
    evi_change_ci95_lo = u_d_evi$ci95_lo,
    evi_change_ci95_hi = u_d_evi$ci95_hi,

    # ---- uncertainty: LST ----
    summer_lst_count   = u_s_lst$count,
    summer_lst_stddev  = u_s_lst$stdDev,
    summer_lst_stderr  = u_s_lst$stdError,
    summer_lst_ci95_lo = u_s_lst$ci95_lo,
    summer_lst_ci95_hi = u_s_lst$ci95_hi,

    winter_lst_count   = u_w_lst$count,
    winter_lst_stddev  = u_w_lst$stdDev,
    winter_lst_stderr  = u_w_lst$stdError,
    winter_lst_ci95_lo = u_w_lst$ci95_lo,
    winter_lst_ci95_hi = u_w_lst$ci95_hi,

    lst_change_count   = u_d_lst$count,
    lst_change_stddev  = u_d_lst$stdDev,
    lst_change_stderr  = u_d_lst$stdError,
    lst_change_ci95_lo = u_d_lst$ci95_lo,
    lst_change_ci95_hi = u_d_lst$ci95_hi
  )
}

# ---- Flatten ALL cities/years (preallocated, year-filtered) ----
city_names <- names(raw)

get_year_keys <- function(city_obj) {
  y <- names(city_obj)
  y[grepl("^[0-9]{4}$", y)]
}

total_rows <- sum(vapply(city_names, function(c) length(get_year_keys(raw[[c]])), integer(1)))
stats_list <- vector("list", max(1L, total_rows))  # guard empty

k <- 0L
for (city in city_names) {
  years <- get_year_keys(raw[[city]])
  for (year in years) {
    k <- k + 1L
    stats_list[[k]] <- flatten_city_year(city, year, raw[[city]][[year]])
  }
}
if (k == 0L) stop("No city-year entries found in JSON.")
if (k < length(stats_list)) stats_list <- stats_list[seq_len(k)]

stats_wide <- dplyr::bind_rows(stats_list) |>
  dplyr::arrange(city, year)

# ---- Quick report ----
print(utils::head(stats_wide, 20))
cat("\nRows:", nrow(stats_wide),
    "  Columns:", ncol(stats_wide),
    "  Cities:", length(unique(stats_wide$city)),
    "  Years:", paste(range(stats_wide$year, na.rm = TRUE), collapse = "–"), "\n")

# ---- Complete years + fill missing values ----
years_full <- 2016:2024
stats_complete <- stats_wide %>%
  group_by(city) %>%
  complete(year = years_full) %>%
  arrange(city, year, .by_group = TRUE) %>%
  ungroup()

fill_city_series <- function(df_city) {
  num_cols <- setdiff(names(df_city), c("city", "year"))
  for (col in num_cols) {
    y <- suppressWarnings(as.numeric(df_city[[col]]))
    # (a) interior linear interpolation
    if (sum(!is.na(y)) >= 2) {
      interp <- approx(
        x = df_city$year[!is.na(y)],
        y = y[!is.na(y)],
        xout = df_city$year,
        method = "linear",
        rule = 1,
        ties = "ordered"
      )$y
    } else {
      interp <- y
    }
    # (b) edge prediction via OLS if still NA
    still_na <- is.na(interp)
    if (any(still_na)) {
      if (sum(!is.na(y)) >= 2) {
        fit <- lm(y ~ year, data = transform(df_city, y = y))
        interp[still_na] <- predict(fit, newdata = df_city[still_na, , drop = FALSE])
      } else if (sum(!is.na(y)) == 1) {
        interp[still_na] <- y[which(!is.na(y))[1]]
      }
    }
    df_city[[col]] <- interp
  }
  df_city
}

stats_filled <- stats_complete %>%
  group_by(city) %>%
  group_modify(~ fill_city_series(.x)) %>%
  ungroup()

# ---- Save ----
dir.create("out", showWarnings = FALSE, recursive = TRUE)
utils::write.csv(stats_filled, "out/stats_filled.csv", row.names = FALSE)
message("Saved: out/stats_filled.csv")
