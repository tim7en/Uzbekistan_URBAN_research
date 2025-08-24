# ==========================================================
# Nightlights: City-Year Plots with Confidence Intervals
# Input : out/nightlights_flat.csv  (from the flatten step)
# Output: out/nightlights_* (PNG/HTML)
# ==========================================================

# -------- Packages --------
pkgs <- c("readr","dplyr","tidyr","ggplot2","scales","forcats")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# -------- Load --------
in_file <- "out/nightlights_flat.csv"
out_dir <- "out"
if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

nl <- readr::read_csv(in_file, show_col_types = FALSE)

# Expect columns like:
# city, year, urban_core_mean, urban_core_sd, urban_core_count,
#                  rural_ring_mean, rural_ring_sd, rural_ring_count

# -------- Tidy + Confidence Intervals --------
# Pivot: zone in {urban_core, rural_ring}, with .value = mean/sd/count
nl_long <- nl %>%
  tidyr::pivot_longer(
    cols = tidyselect::matches("^(urban_core|rural_ring)_(mean|sd|count)$"),
    names_to   = c("zone", ".value"),
    names_pattern = "^(urban_core|rural_ring)_(mean|sd|count)$"
  ) %>%
  mutate(
    zone = forcats::fct_relevel(zone, "urban_core", "rural_ring"),
    count = as.numeric(count),
    sd    = as.numeric(sd),
    mean  = as.numeric(mean),
    se    = sd / sqrt(pmax(count, 1)),         # guard against divide-by-zero
    ci_lo = mean - 1.96 * se,
    ci_hi = mean + 1.96 * se
  )

# Quick sanity check (optional)
# dplyr::glimpse(nl_long)

# -------- Plot 1: Time-series per city with CI ribbons --------
p_ts <- ggplot(nl_long, aes(x = year, y = mean, color = zone, fill = zone, group = zone)) +
  geom_ribbon(aes(ymin = ci_lo, ymax = ci_hi), alpha = 0.18, color = NA) +
  geom_line(size = 1.05) +
  geom_point(size = 2, stroke = 0.2) +
  facet_wrap(~ city, scales = "free_y") +
  scale_x_continuous(breaks = unique(nl_long$year)) +
  scale_y_continuous(labels = label_number(accuracy = 0.1)) +
  labs(
    title = "Nightlights Intensity by City (2016–2024)",
    subtitle = "Mean (points/lines) with 95% confidence ribbons; colored by zone",
    x = "Year",
    y = "Mean nightlights (units)",
    color = "Zone",
    fill  = "Zone"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position = "top",
    strip.text = element_text(face = "bold")
  )

ggsave(file.path(out_dir, "nightlights_timeseries_by_city_ci.png"),
       plot = p_ts, width = 12, height = 8, dpi = 300)

# -------- Plot 2: Cross-city comparison within each year --------
# Order cities within each year by mean (urban_core by default) for readability
nl_ranked <- nl_long %>%
  group_by(year, city) %>%
  summarise(mean_any = mean(mean, na.rm = TRUE), .groups = "drop") %>%
  group_by(year) %>%
  arrange(year, desc(mean_any), .by_group = TRUE) %>%
  mutate(city_order = factor(city, levels = unique(city))) %>%
  select(year, city, city_order)

nl_for_facets <- nl_long %>%
  left_join(nl_ranked, by = c("year","city")) %>%
  mutate(city = city_order)

p_xsec <- ggplot(nl_for_facets,
                 aes(x = city, y = mean, color = zone)) +
  geom_pointrange(aes(ymin = ci_lo, ymax = ci_hi),
                  position = position_dodge(width = 0.5),
                  size = 0.5) +
  facet_wrap(~ year, ncol = 3, scales = "free_y") +
  coord_flip() +
  scale_y_continuous(labels = label_number(accuracy = 0.1)) +
  labs(
    title = "Nightlights Across Cities by Year",
    subtitle = "Point = mean, line = 95% CI; cities ordered by overall brightness per year",
    x = "City",
    y = "Mean nightlights (units)",
    color = "Zone"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position = "top",
    strip.text = element_text(face = "bold")
  )

ggsave(file.path(out_dir, "nightlights_cross_city_by_year_ci.png"),
       plot = p_xsec, width = 14, height = 10, dpi = 300)

# -------- Optional: lightweight interactive (if plotly is available) --------
if (!"plotly" %in% rownames(installed.packages())) {
  message("Tip: install.packages('plotly') for an interactive time-series export.")
} else {
  library(plotly)
  p_ts_int <- ggplotly(p_ts, tooltip = c("year","mean","ci_lo","ci_hi","zone","city"))
  htmlwidgets::saveWidget(p_ts_int,
                          file = file.path(out_dir, "nightlights_timeseries_by_city_ci.html"),
                          selfcontained = TRUE)
}

message("Done. Plots saved to 'out/'.")

# ==========================================================
# Nightlights: Rate-of-Change (2016 -> 2024) by City
# Produces color-coded bar charts (percent change & CAGR)
# ==========================================================

# ---- Packages ----
pkgs <- c("readr","dplyr","tidyr","ggplot2","forcats","scales")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Load long/tidy nightlights with means/SD/counts by zone ----
nl <- readr::read_csv("out/nightlights_flat.csv", show_col_types = FALSE)

nl_long <- nl %>%
  tidyr::pivot_longer(
    cols = tidyselect::matches("^(urban_core|rural_ring)_(mean|sd|count)$"),
    names_to   = c("zone", ".value"),
    names_pattern = "^(urban_core|rural_ring)_(mean|sd|count)$"
  ) %>%
  mutate(
    zone  = forcats::fct_relevel(zone, "urban_core","rural_ring"),
    year  = as.integer(year),
    mean  = as.numeric(mean)
  )

# ---- Compute 2016 & 2024 values and rates ----
rng_years <- c(2016L, 2024L)
yrs_diff  <- diff(rng_years) # 8 years

chg <- nl_long %>%
  filter(year %in% rng_years) %>%
  select(city, zone, year, mean) %>%
  tidyr::pivot_wider(names_from = year, values_from = mean, names_prefix = "y_") %>%
  # Guard against division by zero or missing baselines
  mutate(
    abs_change   = y_2024 - y_2016,
    pct_change   = dplyr::if_else(!is.na(y_2016) & y_2016 != 0,
                                  (y_2024 - y_2016) / y_2016 * 100, NA_real_),
    cagr_percent = dplyr::if_else(!is.na(y_2016) & y_2016 > 0 & !is.na(y_2024) & y_2024 > 0,
                                  ((y_2024 / y_2016)^(1/yrs_diff) - 1) * 100, NA_real_)
  )

# Save summary for reference
if (!dir.exists("out")) dir.create("out", recursive = TRUE)
readr::write_csv(chg, "out/nightlights_ratechange_summary.csv")

# ---- Helper: order cities by metric within each zone (for nice facet bars) ----
order_by_metric <- function(df, metric_col) {
  df %>%
    group_by(zone) %>%
    arrange(.by_group = TRUE, desc(.data[[metric_col]])) %>%
    mutate(city = forcats::fct_relevel(city, unique(city))) %>%
    ungroup()
}

# ---- Plot A: Percent change (2016 -> 2024) ----
chg_pct <- order_by_metric(chg, "pct_change")

p_pct <- ggplot(chg_pct, aes(x = city, y = pct_change, fill = pct_change)) +
  geom_col(width = 0.7, color = "white") +
  geom_hline(yintercept = 0, linewidth = 0.4, color = "grey30") +
  coord_flip() +
  facet_wrap(~ zone, ncol = 1, scales = "free_y") +
  scale_fill_gradient2(
    low = "#3B82F6", mid = "#E5E7EB", high = "#EF4444", midpoint = 0,
    name = "Change"
  ) +
  scale_y_continuous(labels = label_number(accuracy = 0.1, suffix = "%")) +
  labs(
    title = "Nightlights Rate of Change by City (2016 → 2024)",
    subtitle = "Percent change of mean brightness; diverging color scale (blue↓, red↑)",
    x = "City", y = "Percent change"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position = "top",
    strip.text = element_text(face = "bold")
  )

ggsave("out/nightlights_ratechange_pct_by_city.png", p_pct, width = 11, height = 8, dpi = 300)

# ---- Plot B: CAGR (compound annual growth rate) ----
chg_cagr <- order_by_metric(chg, "cagr_percent")

p_cagr <- ggplot(chg_cagr, aes(x = city, y = cagr_percent, fill = cagr_percent)) +
  geom_col(width = 0.7, color = "white") +
  geom_hline(yintercept = 0, linewidth = 0.4, color = "grey30") +
  coord_flip() +
  facet_wrap(~ zone, ncol = 1, scales = "free_y") +
  scale_fill_gradient2(
    low = "#3B82F6", mid = "#E5E7EB", high = "#EF4444", midpoint = 0,
    name = "CAGR"
  ) +
  scale_y_continuous(labels = label_number(accuracy = 0.01, suffix = "%")) +
  labs(
    title = "Nightlights Compound Annual Growth Rate (2016 → 2024)",
    subtitle = "CAGR of mean brightness; diverging color scale (blue↓, red↑)",
    x = "City", y = "CAGR"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    panel.grid.minor = element_blank(),
    legend.position = "top",
    strip.text = element_text(face = "bold")
  )

ggsave("out/nightlights_ratechange_cagr_by_city.png", p_cagr, width = 11, height = 8, dpi = 300)

message("Done: saved rate-of-change plots to 'out/'.")
