# ==============================
# Convert auxiliary_batch_results.json → dataframe (fixed & robust)
# ==============================

# ---- Packages ----
pkgs <- c("jsonlite","dplyr","tibble")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Safety / options ----
try(setTimeLimit(cpu = Inf, elapsed = Inf, transient = TRUE), silent = TRUE)
options(stringsAsFactors = FALSE)

# ---- Helpers ----
`%||%` <- function(x, y) if (is.null(x)) y else x
safe_num <- function(x) if (is.null(x)) NA_real_ else suppressWarnings(as.numeric(x))

# ---- Locate & load JSON ----
# Set path_to_json manually if you prefer; otherwise we auto-detect:
if (!exists("path_to_json")) {
  candidates <- c(
    "reports/auxiliary_batch_results.json",
    "auxiliary_batch_results.json",
    "D:/Dev/Uzbekistan_URBAN_research/suhi_analysis_output/reports/auxiliary_batch_results.json"
  )
  path_to_json <- candidates[file.exists(candidates)][1]
}
if (is.na(path_to_json)) stop("JSON not found. Set `path_to_json` to your file path.")
message("Using file: ", path_to_json)

raw <- jsonlite::fromJSON(path_to_json, simplifyVector = FALSE)

# ---- Flatten one city-year ----
flatten_city_year <- function(city_name, year_key, x) {
  s <- x$stats %||% list()
  tibble::tibble(
    city  = city_name,
    year  = as.integer(year_key),
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
    biomass_change_t_per_ha = safe_num(s$biomass_change_t_per_ha)
  )
}

# ---- Flatten ALL cities/years (preallocated, year-filtered) ----
city_names <- names(raw)

# keep only numeric year keys (e.g., "2016" .. "2024")
get_year_keys <- function(city_obj) {
  y <- names(city_obj)
  y[grepl("^[0-9]{4}$", y)]
}

total_rows <- sum(vapply(city_names, function(c) length(get_year_keys(raw[[c]])), integer(1)))
stats_list <- vector("list", total_rows)

k <- 0L
for (city in city_names) {
  years <- get_year_keys(raw[[city]])
  for (year in years) {
    k <- k + 1L
    stats_list[[k]] <- flatten_city_year(city, year, raw[[city]][[year]])
  }
}
# Trim in case of any skipped years
if (k < total_rows) stats_list <- stats_list[seq_len(k)]

stats_wide <- dplyr::bind_rows(stats_list) |>
  dplyr::arrange(city, year)

# ---- Result ----
print(utils::head(stats_wide, 20))
cat("\nRows:", nrow(stats_wide),
    "  Columns:", ncol(stats_wide),
    "  Cities:", length(unique(stats_wide$city)),
    "  Years:", paste(range(stats_wide$year, na.rm = TRUE), collapse = "–"), "\n")


# 1) Make sure every city has rows for all years (2016–2024)
years_full <- 2016:2024
stats_complete <- stats_wide %>%
  group_by(city) %>%
  complete(year = years_full) %>%
  arrange(city, year, .by_group = TRUE) %>%
  ungroup()

# 2) Filler: linear interpolation for interior gaps; OLS for edges
fill_city_series <- function(df_city) {
  num_cols <- setdiff(names(df_city), c("city", "year"))
  for (col in num_cols) {
    y <- df_city[[col]]
    
    # (a) Linear interpolation for interior points
    if (sum(!is.na(y)) >= 2) {
      interp <- approx(
        x = df_city$year[!is.na(y)],
        y = y[!is.na(y)],
        xout = df_city$year,
        method = "linear",
        rule = 1,         # NA outside the observed range (we'll handle next)
        ties = "ordered"
      )$y
    } else {
      interp <- y
    }
    
    # (b) Edge years still NA → predict from per-city linear model
    still_na <- is.na(interp)
    if (any(still_na)) {
      if (sum(!is.na(y)) >= 2) {
        fit <- lm(y ~ year, data = df_city)
        interp[still_na] <- predict(fit, newdata = df_city[still_na, , drop = FALSE])
      } else if (sum(!is.na(y)) == 1) {
        # If only one observed point exists, use that value for all missing
        interp[still_na] <- y[which(!is.na(y))[1]]
      }
      # If no observations exist at all for this column/city, leave as NA
    }
    
    df_city[[col]] <- interp
  }
  df_city
}

stats_filled <- stats_complete %>%
  group_by(city) %>%
  group_modify(~ fill_city_series(.x)) %>%
  ungroup()

# Now use `stats_filled` instead of `stats_wide`
print(head(stats_filled, 20))


# ---- Optional: save to CSV ----
dir.create("out", showWarnings = FALSE)
utils::write.csv(stats_filled, "out/stats_filled.csv", row.names = FALSE)
message("Saved: out/stats_filled.csv")
