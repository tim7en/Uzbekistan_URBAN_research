# ==========================================================
# Flatten Nightlights JSON
# Input: nightlights_summary.json
# Output: out/nightlights_flat.csv
# ==========================================================

# -------- Packages --------
pkgs <- c("jsonlite", "dplyr", "tidyr", "purrr", "readr", "tibble")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# -------- Load JSON --------
path <- "reports/nightlights_summary.json"
raw <- jsonlite::fromJSON(path, simplifyVector = FALSE)

# -------- Flatten helper --------
flatten_city <- function(city_entry) {
  city_name <- city_entry$city
  years <- names(city_entry$years)
  
  map_dfr(years, function(y) {
    stats <- city_entry$years[[y]]$stats
    
    tibble(
      city = city_name,
      year = as.integer(y),
      
      urban_core_mean   = stats$urban_core$mean,
      urban_core_sd     = stats$urban_core$stdDev,
      urban_core_count  = stats$urban_core$count,
      
      rural_ring_mean   = stats$rural_ring$mean,
      rural_ring_sd     = stats$rural_ring$stdDev,
      rural_ring_count  = stats$rural_ring$count
    )
  })
}

# -------- Build full table --------
flat_df <- map_dfr(raw, flatten_city)

# -------- Save --------
out_dir <- "out"
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
out_file <- file.path(out_dir, "nightlights_flat.csv")
write_csv(flat_df, out_file)

message("Flattened nightlights data saved to: ", out_file)
