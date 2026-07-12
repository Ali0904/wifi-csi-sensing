"""
WiFi Signal Propagation Visualizer
Ray-tracing style apartment floor plan with WiFi signal heatmap
Matches the wifi-apartment.gif style: dark background, bright signal rays
"""
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import patheffects
import matplotlib.animation as animation
from scipy.ndimage import gaussian_filter
import time


ROOM_W = 14.0
ROOM_H = 9.0

WALLS = [
    ((0, 0), (14, 0)),
    ((14, 0), (14, 9)),
    ((14, 9), (0, 9)),
    ((0, 9), (0, 0)),
    ((4.5, 0), (4.5, 3.5)),
    ((4.5, 3.5), (7.5, 3.5)),
    ((7.5, 3.5), (7.5, 0)),
    ((0, 3.5), (3, 3.5)),
    ((3, 3.5), (3, 6.5)),
    ((3, 6.5), (0, 6.5)),
    ((7.5, 5), (10.5, 5)),
    ((10.5, 5), (10.5, 9)),
    ((4.5, 6.5), (7.5, 6.5)),
    ((7.5, 6.5), (7.5, 9)),
    ((10.5, 6), (14, 6)),
    ((3, 6.5), (3, 9)),
]

ROOMS = [
    {'name': 'Living Room', 'center': (2.0, 1.75), 'color': '#1a0533'},
    {'name': 'Kitchen', 'center': (6.0, 1.75), 'color': '#1a0533'},
    {'name': 'Bedroom 1', 'center': (12.0, 2.5), 'color': '#1a0533'},
    {'name': 'Bedroom 2', 'center': (2.0, 7.5), 'color': '#1a0533'},
    {'name': 'Hall', 'center': (5.5, 5.0), 'color': '#1a0533'},
    {'name': 'Bedroom 3', 'center': (9.0, 7.5), 'color': '#1a0533'},
    {'name': 'Bathroom', 'center': (12.0, 7.5), 'color': '#1a0533'},
]

ROUTER_X = 11.0
ROUTER_Y = 4.0

NUM_RAYS = 720
MAX_BOUNCES = 6
WALL_ATTENUATION_DB = 6.0
PATH_LOSS_EXPONENT = 2.8
SIGNAL_DBM_AT_1M = -30
NOISE_FLOOR = -95


def wall_segments():
    segs = []
    for (x1, y1), (x2, y2) in WALLS:
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx*dx + dy*dy)
        if length > 0:
            nx = -dy / length
            ny = dx / length
        else:
            nx, ny = 0, 1
        segs.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'nx': nx, 'ny': ny, 'len': length})
    return segs

def ray_segment_intersect(rx, ry, rdx, rdy, sx1, sy1, sx2, sy2):
    dx = sx2 - sx1
    dy = sy2 - sy1
    denom = rdx * dy - rdy * dx
    if abs(denom) < 1e-10:
        return None, None
    t = ((sx1 - rx) * dy - (sy1 - ry) * dx) / denom
    u = ((sx1 - rx) * rdy - (sy1 - ry) * rdx) / denom
    if t > 0.001 and 0 <= u <= 1:
        ix = sx1 + u * dx
        iy = sy1 + u * dy
        return t, (ix, iy)
    return None, None

def reflect(rdx, rdy, nx, ny):
    dot = rdx * nx + rdy * ny
    return rdx - 2 * dot * nx, rdy - 2 * dot * ny

def is_inside_room(x, y):
    if x < 0 or x > ROOM_W or y < 0 or y > ROOM_H:
        return False
    for (x1, y1), (x2, y2) in WALLS:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx*dx + dy*dy)
        if length < 0.1:
            continue
        nx = -dy / length
        ny = dx / length
        if abs(nx) > 0.5:
            if abs(x - cx) < 0.3 and min(y1, y2) < y < max(y1, y2):
                return True
        elif abs(ny) > 0.5:
            if abs(y - cy) < 0.3 and min(x1, x2) < x < max(x1, x2):
                return True
    return True

def propagate_signal(segments):
    grid_res = 100
    grid_x = int(ROOM_W * grid_res) + 1
    grid_y = int(ROOM_H * grid_res) + 1
    signal_db = np.full((grid_y, grid_x), NOISE_FLOOR, dtype=float)
    hit_count = np.zeros((grid_y, grid_x), dtype=float)

    for ray_idx in range(NUM_RAYS):
        angle = 2 * np.pi * ray_idx / NUM_RAYS
        dx = np.cos(angle)
        dy = np.sin(angle)
        x, y = ROUTER_X, ROUTER_Y
        power_db = SIGNAL_DBM_AT_1M
        rdx, rdy = dx, dy

        for bounce in range(MAX_BOUNCES):
            min_t = 1e10
            hit_seg = None
            hit_point = None

            for seg in segments:
                t, pt = ray_segment_intersect(x, y, rdx, rdy, seg['x1'], seg['y1'], seg['x2'], seg['y2'])
                if t is not None and t < min_t:
                    min_t = t
                    hit_seg = seg
                    hit_point = pt

            if hit_point is None:
                break

            dist = min_t
            power_at_hit = power_db - 10 * PATH_LOSS_EXPONENT * np.log10(max(dist, 0.1))

            steps = max(1, int(dist * grid_res / 2))
            for s in range(steps):
                frac = s / steps
                px = x + rdx * dist * frac
                py = y + rdy * dist * frac
                gx = int(px * grid_res)
                gy = int(py * grid_res)
                if 0 <= gx < grid_x and 0 <= gy < grid_y:
                    frac_power = power_db - 10 * PATH_LOSS_EXPONENT * np.log10(max(dist * frac, 0.05))
                    frac_power -= 0.5 * bounce
                    frac_power = max(frac_power, NOISE_FLOOR)
                    if frac_power > signal_db[gy, gx]:
                        signal_db[gy, gx] = frac_power
                    hit_count[gy, gx] += 1

            nx, ny = hit_seg['nx'], hit_seg['ny']
            if rdx * nx + rdy * ny > 0:
                nx, ny = -nx, -ny

            power_db -= WALL_ATTENUATION_DB
            power_db -= 0.5 * bounce
            rdx, rdy = reflect(rdx, rdy, nx, ny)
            x, y = hit_point[0], hit_point[1]

            if power_db < NOISE_FLOOR:
                break

    return signal_db, hit_count

def build_floorplan_image():
    fig, ax = plt.subplots(figsize=(16, 10), facecolor='#050510')
    ax.set_facecolor('#050510')
    ax.set_xlim(-0.5, ROOM_W + 0.5)
    ax.set_ylim(-0.5, ROOM_H + 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.canvas.manager.set_window_title('WiFi Signal Propagation - Ray Tracing')

    fig.suptitle('WiFi Signal Propagation', color='#88aaff', fontsize=14,
                  fontweight='bold', y=0.95, fontfamily='monospace')

    print("[VIZ] Computing signal propagation (ray tracing)...")
    print(f"[VIZ] {NUM_RAYS} rays, {MAX_BOUNCES} max bounces, {WALL_ATTENUATION_DB}dB wall loss")

    segments = wall_segments()
    signal_db, hit_count = propagate_signal(segments)
    print("[VIZ] Ray tracing complete")

    signal_db_smooth = gaussian_filter(signal_db, sigma=2.0)

    cmap_colors = [
        (0.0, '#050510'),
        (0.05, '#10002a'),
        (0.15, '#2d0066'),
        (0.25, '#5500aa'),
        (0.35, '#7700cc'),
        (0.45, '#9933dd'),
        (0.55, '#bb55ee'),
        (0.65, '#dd77ff'),
        (0.75, '#ff6600'),
        (0.85, '#ff9933'),
        (0.92, '#ffcc00'),
        (0.97, '#ffee66'),
        (1.0, '#ffffff'),
    ]
    cmap = LinearSegmentedColormap.from_list('wifi_signal',
        [(v, c) for v, c in cmap_colors], N=512)

    vmin = NOISE_FLOOR
    vmax = SIGNAL_DBM_AT_1M - 5

    img = ax.imshow(signal_db_smooth, extent=(-0.2, ROOM_W + 0.2, -0.2, ROOM_H + 0.2),
                     origin='lower', cmap=cmap, vmin=vmin, vmax=vmax,
                     aspect='equal', interpolation='bilinear', alpha=0.95, zorder=1)

    for (x1, y1), (x2, y2) in WALLS:
        ax.plot([x1, x2], [y1, y2], color='#334466', linewidth=2.5, zorder=3,
                solid_capstyle='round')

    ax.plot(ROUTER_X, ROUTER_Y, 'o', color='#ffffff', markersize=14, zorder=10,
            markeredgecolor='#6688ff', markeredgewidth=2)

    for r in [0.5, 1.0, 1.5]:
        circle = plt.Circle((ROUTER_X, ROUTER_Y), r, fill=False,
                              edgecolor='#4466aa', linewidth=0.5, linestyle='--', alpha=0.3, zorder=2)
        ax.add_patch(circle)

    ax.text(ROUTER_X, ROUTER_Y - 0.6, 'WiFi Router', color='#88aaff', fontsize=8,
            ha='center', fontweight='bold', zorder=10,
            path_effects=[patheffects.withStroke(linewidth=2, foreground='#050510')])

    for room in ROOMS:
        ax.text(room['center'][0], room['center'][1], room['name'],
                color='#556688', fontsize=7, ha='center', va='center', zorder=5,
                fontfamily='monospace', alpha=0.6,
                path_effects=[patheffects.withStroke(linewidth=1, foreground='#050510')])

    cbar = fig.colorbar(img, ax=ax, fraction=0.025, pad=0.02, shrink=0.7)
    cbar.set_label('Signal Strength (dBm)', color='#88aaff', fontsize=10, fontfamily='monospace')
    cbar.ax.yaxis.set_tick_params(color='#88aaff')
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#88aaff', fontsize=8)
    cbar.ax.set_facecolor('#050510')
    cbar.outline.set_edgecolor('#334466')

    stats_text = (
        f"Router: ({ROUTER_X}m, {ROUTER_Y}m)  |  "
        f"Rays: {NUM_RAYS}  |  "
        f"Wall loss: {WALL_ATTENUATION_DB}dB  |  "
        f"Path loss exponent: {PATH_LOSS_EXPONENT}"
    )
    ax.text(ROOM_W / 2, -0.35, stats_text, color='#445566', fontsize=7,
            ha='center', fontfamily='monospace', zorder=5)

    plt.tight_layout()
    return fig, ax, img, signal_db_smooth


class LiveAnimator:
    def __init__(self):
        self.fig, self.ax, self.img, self.signal = build_floorplan_image()
        self.router_x = ROUTER_X
        self.router_y = ROUTER_Y
        self.frame = 0
        self.phase = 0

    def update(self, frame):
        self.frame = frame
        self.phase += 0.05

        pulse = 1.0 + 0.08 * np.sin(self.phase)
        self.ax.collections[0].set_markersize(14 * pulse) if self.ax.collections else None

        for i, child in enumerate(self.ax.get_children()):
            if isinstance(child, plt.Circle):
                old_alpha = child.get_alpha()
                new_alpha = 0.15 + 0.15 * np.sin(self.phase - i * 0.3)
                child.set_alpha(max(0.05, new_alpha))

    def run(self):
        print("[VIZ] Displaying WiFi signal propagation map")
        print("[VIZ] Close window to exit")
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.1)
        ani = animation.FuncAnimation(self.fig, self.update, interval=100,
                                       blit=False, cache_frame_data=False)
        try:
            while plt.get_fignums():
                plt.pause(0.5)
                self.phase += 0.1
        except KeyboardInterrupt:
            pass
        print("[VIZ] Done")


if __name__ == "__main__":
    viz = LiveAnimator()
    viz.run()
