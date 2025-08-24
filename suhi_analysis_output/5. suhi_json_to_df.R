# ==============================
# suhi_batch_summary.json → data frame
# ==============================

# ---- Packages ----
pkgs <- c("jsonlite","purrr","dplyr","tibble")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Helper ops ----
`%||%` <- function(x, y) if (is.null(x)) y else x
as_num <- function(x) suppressWarnings(as.numeric(x))

# ---- Converter ----
convert_suhi_json_to_df <- function(path = "reports/suhi_batch_summary.json") {
  # Read as nested lists to preserve structure
  j <- jsonlite::read_json(path, simplifyVector = FALSE)
  
  rows_by_city <- purrr::imap(j, function(city_list, city_name) {
    purrr::imap(city_list, function(year_obj, year_name) {
      stats <- year_obj$stats %||% list()
      unc   <- stats$uncertainty %||% list()
      u     <- unc$urban_core %||% list()
      r     <- unc$rural_ring %||% list()
      
      ci_u <- (u$ci95 %||% c(NA_real_, NA_real_))
      ci_r <- (r$ci95 %||% c(NA_real_, NA_real_))
      
      tibble::tibble(
        city  = city_name,
        year  = as.integer(year_obj$year %||% as.integer(year_name)),
        
        urban_mean = as_num(stats$urban_mean),
        rural_mean = as_num(stats$rural_mean),
        suhi       = as_num(stats$suhi),
        
        # Uncertainty (urban core)
        urban_stddev  = as_num(u$stdDev),
        urban_count   = as_num(u$count),
        urban_stderr  = as_num(u$stdError),
        urban_ci95_lo = as_num(ci_u[[1]]),
        urban_ci95_hi = as_num(ci_u[[2]]),
        
        # Uncertainty (rural ring)
        rural_stddev  = as_num(r$stdDev),
        rural_count   = as_num(r$count),
        rural_stderr  = as_num(r$stdError),
        rural_ci95_lo = as_num(ci_r[[1]]),
        rural_ci95_hi = as_num(ci_r[[2]]),
        
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

write.csv(suhi_df, file = "out/suhi_batch_summary_flat.csv", row.names = FALSE)
