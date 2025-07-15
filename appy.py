import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime, timedelta

# === Konfigurasi Streamlit ===
st.set_page_config(page_title="Prakiraan Cuaca Kalimantan Utara", layout="wide")
st.title("📍 Prakiraan Cuaca Provinsi Kalimantan Utara")
st.markdown("**Richard_14.24.0008_M8TB**")

# === Fungsi bantu ambil waktu GFS terbaru ===
def get_latest_gfs_time():
    now = datetime.utcnow() - timedelta(hours=6)
    gfs_date = now.strftime('%Y%m%d')
    gfs_hour = ["00", "06", "12", "18"][now.hour // 6]
    return gfs_date, gfs_hour

@st.cache_data
def load_dataset(run_date, run_hour):
    url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    return xr.open_dataset(url)

# === Sidebar kontrol ===
run_date, run_hour = get_latest_gfs_time()
st.sidebar.title("⚙️ Pengaturan")
st.sidebar.info(f"GFS Run: {run_date} jam {run_hour}Z")

forecast_hour = st.sidebar.slider("Jam ke depan", 0, 240, 6, step=3)
parameter = st.sidebar.selectbox("Parameter Cuaca", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

# === Load dataset GFS ===
try:
    ds = load_dataset(run_date, run_hour)
    st.success("✅ Data GFS berhasil dimuat.")
except Exception as e:
    st.error(f"❌ Gagal memuat data: {e}")
    st.stop()

# === Wilayah Kalimantan Utara ===
lat_min, lat_max = 2.0, 5.0
lon_min, lon_max = 114.0, 118.0
lat_slice = slice(lat_min, lat_max) if ds.lat[0] < ds.lat[-1] else slice(lat_max, lat_min)

# === Parameter cuaca ===
is_vector = False
is_contour = False

if "pratesfc" in parameter:
    var = ds["pratesfc"][forecast_hour] * 3600
    label = "Curah Hujan (mm/jam)"
    cmap = "Blues"
elif "tmp2m" in parameter:
    var = ds["tmp2m"][forecast_hour] - 273.15
    label = "Suhu Permukaan (°C)"
    cmap = "coolwarm"
elif "ugrd10m" in parameter:
    u = ds["ugrd10m"][forecast_hour]
    v = ds["vgrd10m"][forecast_hour]
    var = ((u**2 + v**2)**0.5) * 1.94384
    label = "Kecepatan Angin (knot)"
    cmap = "YlGnBu"
    is_vector = True
elif "prmsl" in parameter:
    var = ds["prmslmsl"][forecast_hour] / 100
    label = "Tekanan Permukaan Laut (hPa)"
    cmap = "cool"
    is_contour = True
else:
    st.warning("Parameter tidak dikenali.")
    st.stop()

# === Potong wilayah ===
var = var.sel(lat=lat_slice, lon=slice(lon_min, lon_max))
if is_vector:
    u = u.sel(lat=lat_slice, lon=slice(lon_min, lon_max))
    v = v.sel(lat=lat_slice, lon=slice(lon_min, lon_max))

# === Validasi waktu ===
valid_time = pd.to_datetime(str(ds.time[forecast_hour].values))
valid_str = valid_time.strftime("%HUTC %a %d %b %Y")
tstr = f"t+{forecast_hour:03d}"

# === Koordinat Titik BMKG Yuvai Semaring Long Bawan ===
bmkg_lat = 3.6888
bmkg_lon = 115.7372

# === Plot Peta ===
fig = plt.figure(figsize=(10, 6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lon_min, lon_max, lat_min, lat_max])

# Judul dan waktu validasi
ax.text(0.5, 1.08, f"{label}", transform=ax.transAxes, ha="center",
        fontsize=12, fontweight="bold")
ax.text(0.01, 1.03, f"Valid: {valid_str}", transform=ax.transAxes,
        fontsize=9, ha="left", va="top")
ax.text(0.99, 1.03, f"GFS {run_date} {run_hour}Z {tstr}", transform=ax.transAxes,
        fontsize=9, ha="right", va="top")

# Tampilkan data
if is_contour:
    cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black',
                    linewidths=0.8, transform=ccrs.PlateCarree())
    ax.clabel(cs, fmt="%d", fontsize=8)
else:
    im = var.plot.pcolormesh(ax=ax, transform=ccrs.PlateCarree(),
                             cmap=cmap, add_colorbar=False)
    cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
    cbar.set_label(label)

    if is_vector:
        ax.quiver(var.lon[::2], var.lat[::2], u.values[::2, ::2], v.values[::2, ::2],
                  transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

# Fitur peta dasar
ax.coastlines(resolution='10m', linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)
ax.add_feature(cfeature.LAND, facecolor='lightgray')
ax.add_feature(cfeature.RIVERS, linewidth=0.5)
ax.add_feature(cfeature.LAKES, alpha=0.4)

# Titik lokasi BMKG Yuvai Semaring
ax.plot(bmkg_lon, bmkg_lat, marker='o', color='red', markersize=6, transform=ccrs.PlateCarree())
ax.text(bmkg_lon + 0.03, bmkg_lat, 'BMKG Yuvai Semaring\n(Long Bawan)',
        fontsize=8, transform=ccrs.PlateCarree(), color='red')

# Tampilkan di Streamlit
st.pyplot(fig)
