# ==============================
# suhi_batch_summary.json → flat data frame (day & night aware)
# ==============================

# ---- Packages ----
pkgs <- c("jsonlite","purrr","dplyr","tibble")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Helper ops ----
`%||%` <- function(x, y) if (is.null(x)) y else x
as_num <- function(x) suppressWarnings(as.numeric(x))

# small helper for uncertainty blocks
pull_unc <- function(lst) {
  lst <- lst %||% list()
  ci  <- lst$ci95 %||% c(NA_real_, NA_real_)
  list(
    mean   = as_num(lst$mean),
    stddev = as_num(lst$stdDev),
    count  = as_num(lst$count),
    stderr = as_num(lst$stdError),
    ci_lo  = as_num(ci[[1]]),
    ci_hi  = as_num(ci[[2]])
  )
}

# ---- Converter ----
convert_suhi_json_to_df <- function(path = "reports/suhi_batch_summary.json") {
  j <- jsonlite::read_json(path, simplifyVector = FALSE)
  
  rows_by_city <- purrr::imap(j, function(city_list, city_name) {
    purrr::imap(city_list, function(year_obj, year_name) {
      stats <- year_obj$stats %||% list()
      
      # ---- Day metrics (fallback to legacy keys if needed) ----
      day_urban_mean <- as_num(stats$day_urban_mean %||% stats$urban_mean)
      day_rural_mean <- as_num(stats$day_rural_mean %||% stats$rural_mean)
      suhi_day       <- as_num(stats$suhi_day %||% stats$suhi)
      
      # Uncertainty (day) — fallback to legacy single "uncertainty"
      unc_day <- stats$uncertainty_day %||% stats$uncertainty %||% list()
      u_day   <- pull_unc(unc_day$urban_core)
      r_day   <- pull_unc(unc_day$rural_ring)
      
      # ---- Night metrics ----
      night_urban_mean <- as_num(stats$night_urban_mean)
      night_rural_mean <- as_num(stats$night_rural_mean)
      suhi_night       <- as_num(stats$suhi_night)
      
      # Uncertainty (night) — may be missing in legacy
      unc_night <- stats$uncertainty_night %||% list()
      u_night   <- pull_unc(unc_night$urban_core)
      r_night   <- pull_unc(unc_night$rural_ring)
      
      # ---- Derived / flags ----
      suhi_day_night_diff   <- as_num(stats$suhi_day_night_diff %||% (suhi_day - suhi_night))
      day_stronger_than_night <- isTRUE(stats$day_stronger_than_night)
      
      tibble::tibble(
        city  = city_name,
        year  = as.integer(year_obj$year %||% as.integer(year_name)),
        
        # Day block
        day_urban_mean = day_urban_mean,
        day_rural_mean = day_rural_mean,
        suhi_day       = suhi_day,
        
        day_urban_stddev  = u_day$stddev,
        day_urban_count   = u_day$count,
        day_urban_stderr  = u_day$stderr,
        day_urban_ci95_lo = u_day$ci_lo,
        day_urban_ci95_hi = u_day$ci_hi,
        
        day_rural_stddev  = r_day$stddev,
        day_rural_count   = r_day$count,
        day_rural_stderr  = r_day$stderr,
        day_rural_ci95_lo = r_day$ci_lo,
        day_rural_ci95_hi = r_day$ci_hi,
        
        # Night block
        night_urban_mean = night_urban_mean,
        night_rural_mean = night_rural_mean,
        suhi_night       = suhi_night,
        
        night_urban_stddev  = u_night$stddev,
        night_urban_count   = u_night$count,
        night_urban_stderr  = u_night$stderr,
        night_urban_ci95_lo = u_night$ci_lo,
        night_urban_ci95_hi = u_night$ci_hi,
        
        night_rural_stddev  = r_night$stddev,
        night_rural_count   = r_night$count,
        night_rural_stderr  = r_night$stderr,
        night_rural_ci95_lo = r_night$ci_lo,
        night_rural_ci95_hi = r_night$ci_hi,
        
        # Comparison / flags
        suhi_day_night_diff   = suhi_day_night_diff,
        day_stronger_than_night = day_stronger_than_night,
        
        # Path
        summary_json = year_obj$summary_json %||% NA_character_
      )
    }) |> purrr::list_rbind()
  }) |> purrr::list_rbind()
  
  dplyr::arrange(rows_by_city, city, year)
}

# ---- Run ----
suhi_df <- convert_suhi_json_to_df("reports/suhi_batch_summary.json")

# Quick peek
print(dplyr::glimpse(suhi_df))

# Optional: save to CSV
dir.create("out", showWarnings = FALSE, recursive = TRUE)
write.csv(suhi_df, file = "out/suhi_batch_summary_flat.csv", row.names = FALSE)
