# ==============================
# SUHI charts: 2016 vs 2024 (+ dashboard-style chart)
# ==============================

# ---- Packages ----
pkgs <- c("readr","dplyr","tidyr","ggplot2","forcats","stringr","scales","tibble","broom")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Input ----
data_path <- "out/suhi_batch_summary_flat.csv"

# ---- Read ----
df_raw <- readr::read_csv(data_path, show_col_types = FALSE)

# ---- Helpers ----
num <- function(x) suppressWarnings(as.numeric(x))
safe_se_from_ci <- function(lo, hi) num( (hi - lo) / (2 * 1.96) )

# ==============================
# Build tidy SUHI table with means, SEs, and CIs for Day/Night
# ==============================
df_suhi <- df_raw %>%
  mutate(
    city = as.character(city),
    year = as.integer(year),
    
    # component SE (urban/rural) -> SUHI SE via propagation
    se_u_day   = dplyr::coalesce(num(day_urban_stderr),  safe_se_from_ci(day_urban_ci95_lo,  day_urban_ci95_hi)),
    se_r_day   = dplyr::coalesce(num(day_rural_stderr),  safe_se_from_ci(day_rural_ci95_lo,  day_rural_ci95_hi)),
    se_day     = sqrt(se_u_day^2 + se_r_day^2),
    
    se_u_night = dplyr::coalesce(num(night_urban_stderr), safe_se_from_ci(night_urban_ci95_lo, night_urban_ci95_hi)),
    se_r_night = dplyr::coalesce(num(night_rural_stderr), safe_se_from_ci(night_rural_ci95_lo, night_rural_ci95_hi)),
    se_night   = sqrt(se_u_night^2 + se_r_night^2),
    
    suhi_day   = num(suhi_day),
    suhi_night = num(suhi_night),
    
    suhi_day_lo   = suhi_day   - 1.96 * se_day,
    suhi_day_hi   = suhi_day   + 1.96 * se_day,
    suhi_night_lo = suhi_night - 1.96 * se_night,
    suhi_night_hi = suhi_night + 1.96 * se_night
  ) %>%
  select(
    city, year,
    suhi_day,   se_day,   suhi_day_lo,   suhi_day_hi,
    suhi_night, se_night, suhi_night_lo, suhi_night_hi
  )

# Long form for plotting + for trends
suhi_long <- df_suhi %>%
  tidyr::pivot_longer(
    c(suhi_day, se_day, suhi_day_lo, suhi_day_hi,
      suhi_night, se_night, suhi_night_lo, suhi_night_hi),
    names_to = "key", values_to = "val"
  ) %>%
  mutate(
    metric = dplyr::case_when(grepl("^suhi_day|^se_day|^suhi_day_", key) ~ "Day",
                              TRUE                                        ~ "Night"),
    stat   = dplyr::case_when(grepl("^suhi_", key) & grepl("_lo$", key) ~ "lo",
                              grepl("^suhi_", key) & grepl("_hi$", key) ~ "hi",
                              grepl("^se_",   key)                      ~ "se",
                              TRUE                                      ~ "mean")
  ) %>%
  select(-key) %>%
  tidyr::pivot_wider(names_from = stat, values_from = val) %>%
  mutate(
    se  = dplyr::coalesce(se, (hi - lo) / (2 * 1.96)),
    lo  = dplyr::coalesce(lo, mean - 1.96 * se),
    hi  = dplyr::coalesce(hi, mean + 1.96 * se)
  ) %>%
  rename(suhi = mean)

# Keep 2016 & 2024 only for level/Δ plots; ensure both years exist per city/metric
suhi_2yrs <- suhi_long %>%
  filter(year %in% c(2016, 2024))

chg <- suhi_2yrs %>%
  select(city, metric, year, suhi, se) %>%
  tidyr::pivot_wider(names_from = year, values_from = c(suhi, se), names_prefix = "Y") %>%
  filter(!is.na(suhi_Y2016), !is.na(suhi_Y2024)) %>%           # <-- guard missing years
  mutate(
    change     = suhi_Y2024 - suhi_Y2016,
    se_change  = sqrt(se_Y2024^2 + se_Y2016^2),
    lo_change  = change - 1.96 * se_change,
    hi_change  = change + 1.96 * se_change
  )

# Order cities by average change (so Day/Night have same order)
city_levels <- chg %>%
  group_by(city) %>%
  summarise(order_val = mean(change, na.rm = TRUE), .groups = "drop") %>%
  arrange(order_val) %>%
  pull(city)

# ---- PLOT A: ΔSUHI (2024−2016) with CI ----
out_dir <- "plots"; if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)
pd <- position_dodge(width = 0.75)

p_change <- ggplot(
  chg,
  aes(x = factor(city, levels = city_levels),
      y = change,
      fill = metric)
) +
  geom_col(position = pd, width = 0.7) +
  geom_errorbar(aes(ymin = lo_change, ymax = hi_change), position = pd, width = 0.25) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  coord_flip() +
  labs(
    title = "ΔSUHI (2024 − 2016) by city with 95% CI",
    subtitle = "Bars show SUHI change; error bars are 95% CIs of the change",
    x = "City",
    y = "Change in SUHI (°C)",
    fill = "Metric"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "top")

ggsave(file.path(out_dir, "06_delta_suhi_2024_minus_2016_by_city_with_CI.png"),
       p_change, width = 12, height = 8, dpi = 300)

# ---- PLOT B1/B2: Levels 2016 vs 2024 ----
p_levels_day <- ggplot(
  suhi_2yrs %>% filter(metric == "Day") %>%
    mutate(city_f = factor(city, levels = city_levels)),
  aes(x = city_f, y = suhi, fill = factor(year))
) +
  geom_col(position = pd, width = 0.7) +
  geom_errorbar(aes(ymin = lo, ymax = hi), position = pd, width = 0.25) +
  coord_flip() + geom_hline(yintercept = 0, linetype = "dashed") +
  labs(title = "SUHI levels by city (2016 vs 2024) — Day",
       subtitle = "Bars = mean SUHI; whiskers = 95% CI",
       x = "City", y = "Daytime SUHI (°C)", fill = "Year") +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "07a_suhi_levels_DAY_2016_vs_2024_by_city_with_CI.png"),
       p_levels_day, width = 12, height = 9, dpi = 300)

p_levels_night <- ggplot(
  suhi_2yrs %>% filter(metric == "Night") %>%
    mutate(city_f = factor(city, levels = city_levels)),
  aes(x = city_f, y = suhi, fill = factor(year))
) +
  geom_col(position = pd, width = 0.7) +
  geom_errorbar(aes(ymin = lo, ymax = hi), position = pd, width = 0.25) +
  coord_flip() + geom_hline(yintercept = 0, linetype = "dashed") +
  labs(title = "SUHI levels by city (2016 vs 2024) — Night",
       subtitle = "Bars = mean SUHI; whiskers = 95% CI",
       x = "City", y = "Nighttime SUHI (°C)", fill = "Year") +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "07b_suhi_levels_NIGHT_2016_vs_2024_by_city_with_CI.png"),
       p_levels_night, width = 12, height = 9, dpi = 300)

# ==============================
# ΔSUHI relative error (stabilized)
# ==============================
REL_EPS <- 0.3  # °C floor to avoid blow-ups when change ~ 0

chg_rel <- chg %>%
  mutate(
    ci_width   = hi_change - lo_change,
    denom      = pmax(abs(change), REL_EPS),
    rel_error  = (ci_width / denom) * 100
  )

p_change_ci <- ggplot(
  chg_rel,
  aes(x = factor(city, levels = city_levels), y = change, fill = metric)
) +
  geom_col(position = pd, width = 0.7, alpha = 0.85) +
  geom_errorbar(aes(ymin = lo_change, ymax = hi_change), position = pd, width = 0.25) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  coord_flip() +
  labs(title = "ΔSUHI (2024 − 2016) with 95% CI",
       subtitle = "Bars = SUHI change; error bars = 95% CI",
       x = "City", y = "Change in SUHI (°C)", fill = "Metric") +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "08a_delta_suhi_with_CI.png"),
       p_change_ci, width = 12, height = 8, dpi = 300)

p_rel_error <- ggplot(
  chg_rel,
  aes(x = factor(city, levels = city_levels), y = rel_error, fill = metric)
) +
  geom_col(position = pd, width = 0.7, alpha = 0.8) +
  coord_flip() +
  labs(title = "Relative Error of ΔSUHI (stabilized)",
       subtitle = sprintf("CI width / max(|ΔSUHI|, %.1f°C) expressed as %%", REL_EPS),
       x = "City", y = "Relative error (%)", fill = "Metric") +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "08b_delta_suhi_relative_error.png"),
       p_rel_error, width = 12, height = 8, dpi = 300)

# ==============================
# Relative Error on levels (2016 vs 2024), like your example
# ==============================
RELERR_METRIC <- "Day"   # or "Night"
cols_thresh <- c("Green (≤10%)" = "#2ECC71", "Orange (10–30%)" = "#F39C12", "Red (>30%)" = "#E74C3C")

rel_df <- suhi_long %>%
  filter(metric == RELERR_METRIC, year %in% c(2016, 2024)) %>%
  mutate(
    ci_width    = (hi - lo),
    denom       = pmax(abs(suhi), 1e-6),
    rel_err_pct = (ci_width / denom) * 100,
    thresh = case_when(
      is.na(rel_err_pct)   ~ NA_character_,
      rel_err_pct <= 10    ~ "Green (≤10%)",
      rel_err_pct <= 30    ~ "Orange (10–30%)",
      TRUE                 ~ "Red (>30%)"
    )
  )

# order by 2024 rel error (desc)
city_levels_rel <- rel_df %>%
  filter(year == 2024) %>%
  arrange(desc(rel_err_pct)) %>%
  pull(city) %>%
  unique()
if (!length(city_levels_rel)) city_levels_rel <- unique(rel_df$city)

rel_df <- rel_df %>%
  mutate(
    city_f = factor(city, levels = city_levels_rel),
    label  = paste0(sprintf("%.1f", rel_err_pct), "%"),
    lab_col = ifelse(rel_err_pct > 30, "white", "black")
  )

pd2 <- position_dodge(width = 0.75)

p_rel_levels <- ggplot(rel_df, aes(x = city_f, y = rel_err_pct)) +
  geom_col(aes(fill = thresh, alpha = factor(year)), position = pd2, width = 0.7) +
  geom_text(aes(label = label, group = year, alpha = factor(year), color = lab_col),
            position = pd2, vjust = -0.2, size = 3, show.legend = FALSE) +
  scale_fill_manual(values = cols_thresh, na.value = "grey80") +
  scale_alpha_manual(values = c("2016" = 0.6, "2024" = 0.95), name = NULL,
                     labels = c("2016" = "Relative Error 2016 (%)",
                                "2024" = "Relative Error 2024 (%)")) +
  scale_color_identity() +
  coord_flip(clip = "off") +
  geom_hline(yintercept = 10, linetype = "dotted") +
  geom_hline(yintercept = 30, linetype = "dotted") +
  labs(
    title = sprintf("Relative Error Analysis: 2016 vs 2024 — %s SUHI", RELERR_METRIC),
    subtitle = "Color coding: Green ≤10% | Orange 10–30% | Red >30% • Bars show 95% CI width relative to |SUHI|",
    x = "Cities", y = "Relative Error (%)", fill = "Threshold"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "top", plot.margin = margin(10, 30, 10, 10))

ggsave(file.path(out_dir, sprintf("08c_relative_error_levels_2016_vs_2024_%s.png", tolower(RELERR_METRIC))),
       p_rel_levels, width = 12, height = 8, dpi = 300)

# ==============================
# SUHI trends over time (2016–2024) for each city (FIXED)
# ==============================

# create df_trend from the long table (all years)
df_trend <- suhi_long %>%
  select(city, year, metric, suhi, lo, hi) %>%
  filter(!is.na(year), !is.na(suhi))

# p-values for slope of suhi ~ year by city×metric
trend_stats <- df_trend %>%
  group_by(city, metric) %>%
  do({
    fit <- try(lm(suhi ~ year, data = .), silent = TRUE)
    if (inherits(fit, "try-error")) {
      tibble(pval = NA_real_)
    } else {
      broom::tidy(fit) %>%
        filter(term == "year") %>%
        transmute(pval = p.value)
    }
  }) %>%
  ungroup() %>%
  mutate(
    stars = case_when(
      is.na(pval)  ~ "",
      pval < 0.001 ~ "***",
      pval < 0.01  ~ "**",
      pval < 0.05  ~ "*",
      TRUE         ~ "ns"
    ),
    label = paste0("p=", ifelse(is.na(pval), "NA", formatC(pval, format="g", digits=3)),
                   " ", stars)
  )

# ranges for fixed annotation positions
ranges <- df_trend %>%
  group_by(city) %>%
  summarise(
    xmin = min(year, na.rm = TRUE),
    xmax = max(year, na.rm = TRUE),
    ymin = min(lo,   na.rm = TRUE),
    ymax = max(hi,   na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(
    xrange = pmax(xmax - xmin, 1e-6),
    yrange = pmax(ymax - ymin, 1e-6)
  )

annot <- trend_stats %>%
  left_join(ranges, by = "city") %>%
  mutate(
    m_rank = ifelse(metric == "Day", 1L, 2L),
    x = xmax - 0.02 * xrange,
    y = ymax - (0.02 + (m_rank - 1) * 0.10) * yrange
  )

p_trend_pvals <- ggplot(df_trend,
                        aes(x = year, y = suhi, color = metric, fill = metric, group = metric)) +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.15, color = NA) +
  geom_line(size = 1) +
  geom_point(size = 1.8) +
  facet_wrap(~ city, scales = "free_y") +
  geom_label(
    data = annot,
    aes(x = x, y = y, label = label, color = metric),
    inherit.aes = FALSE,
    hjust = 1, vjust = 1,
    label.size = 0,
    fill = "white", alpha = 0.7,
    size = 3
  ) +
  labs(
    title = "Year-over-year SUHI trends (2016–2024)",
    subtitle = "Day vs Night per city with 95% CI ribbons • annotated with p-values",
    x = "Year", y = "SUHI (°C)", color = "Metric", fill  = "Metric"
  ) +
  theme_minimal(base_size = 11) +
  theme(legend.position = "top")

ggsave(file.path(out_dir, "11_suhi_trends_per_city_with_colored_pvals.png"),
       p_trend_pvals, width = 14, height = 10, dpi = 300)
