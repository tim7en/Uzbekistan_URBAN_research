# ==============================
# LST charts: 2016 vs 2024 (+ trends, relative error)
# (Updated for stats_filled.csv with summer/winter LST + uncertainty)
# ==============================

# ---- Packages ----
pkgs <- c("readr","dplyr","tidyr","ggplot2","forcats","stringr","scales","tibble","broom")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

# ---- Input ----
data_path <- "suhi_analysis_output/out/stats_filled.csv"

# ---- Read ----
df_raw <- readr::read_csv(data_path, show_col_types = FALSE)

# ---- Helpers ----
num <- function(x) suppressWarnings(as.numeric(x))
safe_se_from_ci <- function(lo, hi) num( (hi - lo) / (2 * 1.96) )

# ==============================
# Build tidy LST table with means, SEs, and CIs for Summer/Winter
# ==============================
df_lst <- df_raw %>%
  mutate(
    city = as.character(city),
    year = as.integer(year),

    # Prefer *_stderr; if missing, derive from ci95
    se_summer = dplyr::coalesce(num(summer_lst_stderr),
                                safe_se_from_ci(summer_lst_ci95_lo, summer_lst_ci95_hi)),
    se_winter = dplyr::coalesce(num(winter_lst_stderr),
                                safe_se_from_ci(winter_lst_ci95_lo, winter_lst_ci95_hi)),

    lst_summer = num(summer_lst_mean),
    lst_winter = num(winter_lst_mean),

    summer_lo = lst_summer - 1.96 * se_summer,
    summer_hi = lst_summer + 1.96 * se_summer,
    winter_lo = lst_winter - 1.96 * se_winter,
    winter_hi = lst_winter + 1.96 * se_winter
  ) %>%
  select(
    city, year,
    lst_summer, se_summer, summer_lo, summer_hi,
    lst_winter, se_winter, winter_lo, winter_hi
  )

# Long form for plotting + trends
lst_long <- df_lst %>%
  tidyr::pivot_longer(
    cols = c(lst_summer, se_summer, summer_lo, summer_hi,
             lst_winter, se_winter, winter_lo, winter_hi),
    names_to = "key", values_to = "val"
  ) %>%
  mutate(
    metric = dplyr::case_when(grepl("^lst_summer|^se_summer|^summer_", key) ~ "Summer",
                              TRUE                                           ~ "Winter"),
    stat   = dplyr::case_when(
               grepl("^lst_", key)                 ~ "mean",
               grepl("_lo$",  key)                 ~ "lo",
               grepl("_hi$",  key)                 ~ "hi",
               grepl("^se_",  key)                 ~ "se",
               TRUE                                ~ NA_character_
             )
  ) %>%
  select(-key) %>%
  tidyr::pivot_wider(names_from = stat, values_from = val) %>%
  mutate(
    se  = dplyr::coalesce(se, (hi - lo) / (2 * 1.96)),
    lo  = dplyr::coalesce(lo, mean - 1.96 * se),
    hi  = dplyr::coalesce(hi, mean + 1.96 * se)
  ) %>%
  rename(lst = mean)

# Keep 2016 & 2024 only for level/Δ plots; ensure both years exist per city/metric
lst_2yrs <- lst_long %>%
  filter(year %in% c(2016, 2024))

chg <- lst_2yrs %>%
  select(city, metric, year, lst, se) %>%
  tidyr::pivot_wider(names_from = year, values_from = c(lst, se), names_prefix = "Y") %>%
  filter(!is.na(lst_Y2016), !is.na(lst_Y2024)) %>%
  mutate(
    change     = lst_Y2024 - lst_Y2016,
    se_change  = sqrt(se_Y2024^2 + se_Y2016^2),
    lo_change  = change - 1.96 * se_change,
    hi_change  = change + 1.96 * se_change
  )

# Order cities by average change so Summer/Winter share the same order
city_levels <- chg %>%
  group_by(city) %>%
  summarise(order_val = mean(change, na.rm = TRUE), .groups = "drop") %>%
  arrange(order_val) %>%
  pull(city)

# ---- PLOT A: ΔLST (2024−2016) with CI ----
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
    title = "ΔLST (2024 − 2016) by city with 95% CI",
    subtitle = "Bars show change in Summer/Winter LST; error bars are 95% CIs of the change",
    x = "City",
    y = "Change in LST (°C)",
    fill = "Season"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "top")

ggsave(file.path(out_dir, "06_delta_LST_2024_minus_2016_by_city_with_CI.png"),
       p_change, width = 12, height = 8, dpi = 300)

# ---- PLOT B1/B2: Levels 2016 vs 2024 ----
p_levels_summer <- ggplot(
  lst_2yrs %>% filter(metric == "Summer") %>%
    mutate(city_f = factor(city, levels = city_levels)),
  aes(x = city_f, y = lst, fill = factor(year))
) +
  geom_col(position = pd, width = 0.7) +
  geom_errorbar(aes(ymin = lo, ymax = hi), position = pd, width = 0.25) +
  coord_flip() + geom_hline(yintercept = 0, linetype = "dashed") +
  labs(title = "LST levels by city (2016 vs 2024) — Summer",
       subtitle = "Bars = mean LST; whiskers = 95% CI",
       x = "City", y = "Summer LST (°C)", fill = "Year") +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "07a_LST_levels_SUMMER_2016_vs_2024_by_city_with_CI.png"),
       p_levels_summer, width = 12, height = 9, dpi = 300)

p_levels_winter <- ggplot(
  lst_2yrs %>% filter(metric == "Winter") %>%
    mutate(city_f = factor(city, levels = city_levels)),
  aes(x = city_f, y = lst, fill = factor(year))
) +
  geom_col(position = pd, width = 0.7) +
  geom_errorbar(aes(ymin = lo, ymax = hi), position = pd, width = 0.25) +
  coord_flip() + geom_hline(yintercept = 0, linetype = "dashed") +
  labs(title = "LST levels by city (2016 vs 2024) — Winter",
       subtitle = "Bars = mean LST; whiskers = 95% CI",
       x = "City", y = "Winter LST (°C)", fill = "Year") +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "07b_LST_levels_WINTER_2016_vs_2024_by_city_with_CI.png"),
       p_levels_winter, width = 12, height = 9, dpi = 300)

# ==============================
# ΔLST relative error (stabilized)
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
  labs(title = "ΔLST (2024 − 2016) with 95% CI",
       subtitle = "Bars = change; error bars = 95% CI",
       x = "City", y = "Change in LST (°C)", fill = "Season") +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "08a_delta_LST_with_CI.png"),
       p_change_ci, width = 12, height = 8, dpi = 300)

p_rel_error <- ggplot(
  chg_rel,
  aes(x = factor(city, levels = city_levels), y = rel_error, fill = metric)
) +
  geom_col(position = pd, width = 0.7, alpha = 0.8) +
  coord_flip() +
  labs(title = "Relative Error of ΔLST (stabilized)",
       subtitle = sprintf("CI width / max(|Δ|, %.1f°C) expressed as %%", REL_EPS),
       x = "City", y = "Relative error (%)", fill = "Season") +
  scale_y_continuous(labels = function(x) paste0(x, "%")) +
  theme_minimal(base_size = 12) + theme(legend.position = "top")

ggsave(file.path(out_dir, "08b_delta_LST_relative_error.png"),
       p_rel_error, width = 12, height = 8, dpi = 300)

# ==============================
# Relative Error on levels (2016 vs 2024), Summer/Winter
# ==============================
RELERR_METRIC <- "Summer"   # or "Winter"
cols_thresh <- c("Green (≤10%)" = "#2ECC71", "Orange (10–30%)" = "#F39C12", "Red (>30%)" = "#E74C3C")

rel_df <- lst_long %>%
  filter(metric == RELERR_METRIC, year %in% c(2016, 2024)) %>%
  mutate(
    ci_width    = (hi - lo),
    denom       = pmax(abs(lst), 1e-6),
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
    title = sprintf("Relative Error Analysis: 2016 vs 2024 — %s LST", RELERR_METRIC),
    subtitle = "Color coding: Green ≤10% | Orange 10–30% | Red >30% • Bars show 95% CI width relative to |LST|",
    x = "Cities", y = "Relative Error (%)", fill = "Threshold"
  ) +
  theme_minimal(base_size = 12) +
  theme(legend.position = "top", plot.margin = margin(10, 30, 10, 10))

ggsave(file.path(out_dir, sprintf("08c_relative_error_levels_2016_vs_2024_%s.png", tolower(RELERR_METRIC))),
       p_rel_levels, width = 12, height = 8, dpi = 300)

# ==============================
# LST trends over time (2016–2024) for each city
# ==============================
df_trend <- lst_long %>%
  select(city, year, metric, lst, lo, hi) %>%
  filter(!is.na(year), !is.na(lst))

# p-values for slope of lst ~ year by city×metric
trend_stats <- df_trend %>%
  group_by(city, metric) %>%
  do({
    fit <- try(lm(lst ~ year, data = .), silent = TRUE)
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
    m_rank = ifelse(metric == "Summer", 1L, 2L),
    x = xmax - 0.02 * xrange,
    y = ymax - (0.02 + (m_rank - 1) * 0.10) * yrange
  )

p_trend_pvals <- ggplot(df_trend,
                        aes(x = year, y = lst, color = metric, fill = metric, group = metric)) +
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
    title = "Year-over-year LST trends (2016–2024)",
    subtitle = "Summer vs Winter per city with 95% CI ribbons • annotated with p-values",
    x = "Year", y = "LST (°C)", color = "Season", fill  = "Season"
  ) +
  theme_minimal(base_size = 11) +
  theme(legend.position = "top")

ggsave(file.path(out_dir, "11_LST_trends_per_city_with_colored_pvals.png"),
       p_trend_pvals, width = 14, height = 10, dpi = 300)
