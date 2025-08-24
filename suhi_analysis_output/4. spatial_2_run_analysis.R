# ==========================================================
# City-level change table (wide) -> plots
# Expects columns like:
#   city, veg_patch_count_change, veg_patch_count_pct,
#   veg_mean_patch_area_m2_change, veg_mean_patch_area_m2_pct, ...
# Outputs:
#   out/spatial_changes_diverging_<IND>.png
#   out/spatial_changes_heatmap_pct.png
#   out/spatial_changes_lollipop_<IND>.png
# ==========================================================

pkgs <- c("readr","dplyr","tidyr","stringr","forcats","ggplot2","scales")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

dir.create("out", showWarnings = FALSE, recursive = TRUE)

# ---------- Load ----------
# Point this to your table (e.g., out/spatial_temporal_changes.csv)
path <- "out/spatial_temporal_changes.csv"

# Read robustly (treat "NA" as NA)
df <- readr::read_csv(path, na = c("NA",""), show_col_types = FALSE)

# If your column names are abbreviated like in the screenshot,
# you can rename them to friendlier forms here (optional):
# names(df)

# ---------- Coerce numerics ----------
num_cols <- setdiff(names(df), "city")
df <- df %>% mutate(across(all_of(num_cols), as.numeric))

# ---------- Helpers ----------
nice_label <- function(x) {
  x %>%
    str_replace("_pct$"," (%)") %>%
    str_replace_all("_"," ") %>%
    str_to_sentence()
}
theme_pub <- function() {
  theme_minimal(base_size = 12) +
    theme(panel.grid.minor = element_blank(),
          plot.title = element_text(face = "bold"),
          legend.position = "top")
}

# ==========================================================
# 1) Diverging bars for a chosen % change indicator
#    (pick any *_pct column that exists)
# ==========================================================
pct_candidates <- names(df)[str_detect(names(df), "_pct$")]
# Choose one to highlight (change here if you prefer another)
focus_pct <- pct_candidates[1]  # e.g., "veg_patch_count_pct"

if (!is.na(focus_pct)) {
  p_div <- df %>%
    mutate(city = fct_reorder(city, .data[[focus_pct]])) %>%
    ggplot(aes(x = city, y = .data[[focus_pct]], fill = .data[[focus_pct]] > 0)) +
    geom_col(width = 0.7) +
    geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
    coord_flip() +
    scale_fill_manual(values = c("#d73027","#1a9850"), guide = "none") +
    scale_y_continuous(labels = label_percent(scale = 1)) +
    labs(title = paste0(nice_label(focus_pct), " — change 2016→2024"),
         x = NULL, y = "% change") +
    theme_pub()
  ggsave(paste0("out/spatial_changes_diverging_", focus_pct, ".png"),
         p_div, width = 8, height = 5, dpi = 150)
}

# ==========================================================
# 2) Heatmap of all percent changes (cities × indicators)
# ==========================================================
if (length(pct_candidates)) {
  hm <- df %>%
    select(city, all_of(pct_candidates)) %>%
    pivot_longer(-city, names_to = "indicator", values_to = "pct") %>%
    mutate(indicator = nice_label(indicator))
  
  p_hm <- ggplot(hm, aes(x = indicator, y = city, fill = pct)) +
    geom_tile(color = "white", linewidth = 0.3) +
    scale_fill_gradient2(low = "#d73027", mid = "white", high = "#1a9850",
                         midpoint = 0, labels = label_percent(scale = 1)) +
    labs(title = "Percent change by indicator (2016→2024)",
         x = NULL, y = NULL, fill = "% change") +
    theme_pub() +
    theme(axis.text.x = element_text(angle = 30, hjust = 1))
  ggsave("out/spatial_changes_heatmap_pct.png", p_hm, width = 11, height = 6, dpi = 150)
}

# ==========================================================
# 3) Lollipop of absolute change for a chosen indicator
#    (pick any *_change column)
# ==========================================================
chg_candidates <- names(df)[str_detect(names(df), "_change$")]
focus_chg <- chg_candidates[1]  # e.g., "veg_patch_count_change"

if (!is.na(focus_chg)) {
  p_lolli <- df %>%
    mutate(city = fct_reorder(city, .data[[focus_chg]])) %>%
    ggplot(aes(y = city, x = .data[[focus_chg]],
               color = .data[[focus_chg]] > 0)) +
    geom_segment(aes(x = 0, xend = .data[[focus_chg]], y = city, yend = city),
                 linewidth = 0.7) +
    geom_point(size = 3) +
    scale_color_manual(values = c("#d73027","#1a9850"), guide = "none") +
    labs(title = paste0(nice_label(focus_chg), " — absolute change 2016→2024"),
         x = "Change", y = NULL) +
    theme_pub()
  ggsave(paste0("out/spatial_changes_lollipop_", focus_chg, ".png"),
         p_lolli, width = 8, height = 5, dpi = 150)
}

message("✅ Plots saved in 'out/'. You can switch 'focus_pct' / 'focus_chg' to other columns.")


# ==========================================================
# Urban Sprawl vs Vegetation Access: Relationship & Shift
# Reads:
#   - out/spatial_per_year.csv (from your JSON flattener)
# Writes:
#   - out/sprawl_veg_trajectory_table.csv
#   - out/sprawl_veg_quadrant_arrows.png
#   - out/sprawl_veg_facets_ci.png
# ==========================================================

pkgs <- c("readr","dplyr","tidyr","ggplot2","ggrepel","scales","forcats","stringr")
to_install <- setdiff(pkgs, rownames(installed.packages()))
if (length(to_install)) install.packages(to_install, dep = TRUE)
invisible(lapply(pkgs, library, character.only = TRUE))

dir.create("out", showWarnings = FALSE, recursive = TRUE)

# ---------- Load per-year table ----------
per_year_path <- "out/spatial_per_year.csv"
stopifnot(file.exists(per_year_path))
per <- readr::read_csv(per_year_path, show_col_types = FALSE)

# keep only what we need for the bivariate story
per <- per %>%
  select(city, year,
         built_mean_distance_m,
         built_distance_ci95_lo, built_distance_ci95_hi,
         veg_access_mean_m,
         veg_access_ci95_lo, veg_access_ci95_hi) %>%
  filter(year %in% c(2016, 2024))

# ---------- Compute city deltas 2016 → 2024 ----------
traj <- per %>%
  pivot_wider(names_from = year,
              values_from = c(built_mean_distance_m, veg_access_mean_m,
                              built_distance_ci95_lo, built_distance_ci95_hi,
                              veg_access_ci95_lo,  veg_access_ci95_hi),
              names_glue = "{.value}_{year}") %>%
  mutate(
    d_built_m = built_mean_distance_m_2024 - built_mean_distance_m_2016,
    d_veg_m   = veg_access_mean_m_2024     - veg_access_mean_m_2016,
    d_built_pct = 100 * d_built_m / built_mean_distance_m_2016,
    d_veg_pct   = 100 * d_veg_m   / veg_access_mean_m_2016,
    # Trajectory category (how sprawl & veg access moved)
    trajectory = case_when(
      d_built_m < 0 & d_veg_m < 0 ~ "Denser + better veg access",
      d_built_m < 0 & d_veg_m > 0 ~ "Denser + worse veg access",
      d_built_m > 0 & d_veg_m < 0 ~ "Less dense + better veg access",
      d_built_m > 0 & d_veg_m > 0 ~ "Less dense + worse veg access",
      TRUE ~ "Mixed/flat"
    ),
    # Magnitude & direction for extra analytics (optional)
    shift_magnitude = sqrt(d_built_m^2 + d_veg_m^2),
    shift_angle_deg = atan2(d_veg_m, d_built_m) * 180/pi
  )

# Save the table for auditing / reuse
readr::write_csv(traj, "out/sprawl_veg_trajectory_table.csv")

# ---------- Build plotting frames ----------
# segments/arrows from 2016 to 2024
seg <- traj %>%
  transmute(
    city, trajectory,
    x0 = built_mean_distance_m_2016,
    y0 = veg_access_mean_m_2016,
    x1 = built_mean_distance_m_2024,
    y1 = veg_access_mean_m_2024,
    # Numeric label at 2024 end
    label = paste0(
      city, "\n",
      "Built 2024: ", scales::comma(round(x1)), " m (",
      sprintf("%+d", round(d_built_m)), " m, ",
      sprintf("%+.1f", d_built_pct), "%)\n",
      "Veg 2024:   ", scales::comma(round(y1)), " m (",
      sprintf("%+d", round(d_veg_m)), " m, ",
      sprintf("%+.1f", d_veg_pct), "%)"
    )
  )

# points for both years (for endpoints)
pts <- per %>% mutate(year = factor(year))

# CI crosshairs for both years (horizontal = built, vertical = veg)
ci_lines <- per %>%
  transmute(
    city, year,
    x  = built_mean_distance_m,
    xlo = built_distance_ci95_lo,  xhi = built_distance_ci95_hi,
    y  = veg_access_mean_m,
    ylo = veg_access_ci95_lo,      yhi = veg_access_ci95_hi
  )

# Use 2016 medians to draw quadrant guides (robust reference)
med_2016 <- per %>% filter(year == 2016) %>%
  summarise(mx = median(built_mean_distance_m, na.rm = TRUE),
            my = median(veg_access_mean_m,     na.rm = TRUE))

# Colors for trajectory types
traj_pal <- c(
  "Denser + better veg access" = "#1a9850",
  "Denser + worse veg access"  = "#d73027",
  "Less dense + better veg access" = "#66bd63",
  "Less dense + worse veg access"  = "#f46d43",
  "Mixed/flat" = "grey50"
)

# ---------- 1) Quadrant arrow chart with CI crosshairs ----------
p_quad <- ggplot() +
  # Quadrant shading relative to 2016 medians
  annotate("rect",
           xmin = -Inf, xmax = med_2016$mx, ymin = -Inf, ymax = med_2016$my,
           fill = "#f0f9e8", alpha = 0.5) +
  annotate("rect",
           xmin = med_2016$mx, xmax = Inf, ymin = -Inf, ymax = med_2016$my,
           fill = "#fefefe", alpha = 0.5) +
  annotate("rect",
           xmin = -Inf, xmax = med_2016$mx, ymin = med_2016$my, ymax = Inf,
           fill = "#fff7f3", alpha = 0.5) +
  annotate("rect",
           xmin = med_2016$mx, xmax = Inf, ymin = med_2016$my, ymax = Inf,
           fill = "#f7f7f7", alpha = 0.5) +
  # Reference median lines
  geom_vline(xintercept = med_2016$mx, linetype = 3, color = "grey55") +
  geom_hline(yintercept = med_2016$my, linetype = 3, color = "grey55") +
  # CI crosshairs for both years
  geom_errorbarh(
    data = ci_lines,
    aes(y = y, xmin = xlo, xmax = xhi, group = interaction(city, year)),
    height = 0, color = "grey40", alpha = 0.6
  ) +
  geom_errorbar(
    data = ci_lines,
    aes(x = x, ymin = ylo, ymax = yhi, group = interaction(city, year)),
    width = 0, color = "grey40", alpha = 0.6
  ) +
  # Arrows from 2016 to 2024 colored by trajectory
  geom_segment(
    data = seg,
    aes(x = x0, y = y0, xend = x1, yend = y1, color = trajectory),
    linewidth = 0.9,
    arrow = arrow(length = unit(0.16, "cm"), type = "closed")
  ) +
  # Endpoints (points)
  geom_point(
    data = pts,
    aes(x = built_mean_distance_m, y = veg_access_mean_m),
    size = 2.2, color = "black", alpha = 0.75
  ) +
  # Labels with numbers at 2024
  ggrepel::geom_label_repel(
    data = seg,
    aes(x = x1, y = y1, label = label, color = trajectory),
    fill = "white", label.size = 0.25, size = 3.1, show.legend = FALSE,
    min.segment.length = 0, box.padding = 0.25, max.overlaps = Inf
  ) +
  scale_color_manual(values = traj_pal) +
  scale_x_continuous("Built distance to nearest built-up (m)", labels = comma) +
  scale_y_continuous("Vegetation accessibility distance (m)", labels = comma) +
  labs(
    title = "Urban sprawl vs vegetation access: relationship & shift (2016 → 2024)",
    subtitle = "Arrows show per-city change; CI crosshairs are 95% intervals. Left = denser built; Down = closer to vegetation.",
    color = "Trajectory type"
  ) +
  theme_minimal(base_size = 12) +
  theme(panel.grid.minor = element_blank())

ggsave("out/sprawl_veg_quadrant_arrows.png", p_quad, width = 12, height = 8, dpi = 300)
# --- Make a numeric y index: 2016 -> 1, 2024 -> 2 (use everywhere) ---
per_pos <- per %>% mutate(y_idx = ifelse(year == 2016, 1, 2))

# update helpers built from `per`
seg <- seg %>%
  mutate(y0 = 1, y1 = 2)  # already numeric; keep as-is

pts <- per_pos  # points now carry y_idx

ci_lines <- per_pos %>%
  transmute(
    city, year, y_idx,
    x  = built_mean_distance_m,
    xlo = built_distance_ci95_lo,  xhi = built_distance_ci95_hi,
    y  = veg_access_mean_m,
    ylo = veg_access_ci95_lo,      yhi = veg_access_ci95_hi
  )

# --- Faceted small-multiples with consistent numeric y ---
p_facets <- ggplot() +
  geom_errorbarh(
    data = ci_lines,
    aes(y = y_idx, xmin = xlo, xmax = xhi),
    height = 0, color = "grey40", alpha = 0.6
  ) +
  geom_errorbar(
    data = ci_lines,
    aes(x = x, ymin = y_idx - 0.08, ymax = y_idx + 0.08),
    width = 0, color = "grey40", alpha = 0.6
  ) +
  geom_segment(
    data = seg,
    aes(x = x0, y = 1, xend = x1, yend = 2),
    arrow = arrow(length = unit(0.12, "cm"), type = "closed"),
    color = "steelblue"
  ) +
  geom_point(
    data = pts,
    aes(x = built_mean_distance_m, y = y_idx), size = 2.2
  ) +
  facet_wrap(~ city, scales = "free") +
  scale_y_continuous(breaks = c(1, 2), labels = c("2016", "2024")) +
  scale_x_continuous("Built distance (m)", labels = scales::comma) +
  labs(
    title = "Per-city shift in built distance vs vegetation access",
    subtitle = "Arrows show 2016→2024; CI crosshairs are 95% intervals.",
    y = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(panel.grid.minor = element_blank())

ggsave("out/sprawl_veg_facets_ci.png", p_facets, width = 12, height = 8, dpi = 300)
message("✅ Saved:",
        "\n- out/sprawl_veg_trajectory_table.csv",
        "\n- out/sprawl_veg_quadrant_arrows.png",
        "\n- out/sprawl_veg_facets_ci.png")
