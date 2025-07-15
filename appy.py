import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Prakiraan Cuaca Krayan", layout="wide")
st.title("📍 Prakiraan Cuaca Wilayah Krayan (GFS Realtime)")
st.header("Web Hasil Pembelajaran Pengelolaan Informasi Meteorologi")

# ===== Fungsi bantu ambil run time GFS terbaru =====
def get_latest_gfs_time():
    now = datetime.utcnow() - timedelta(hours=6)
    gfs_date = now.strftime('%Y%m%d')
    if now.hour < 6:
        gfs_hour = "00"
    elif now.hour < 12:
        gfs_hour = "06"
    elif now.hour < 18:
        gfs_hour = "12"
    else:
        gfs_hour = "18"
    return gfs_date, gfs_hour

# ===== Fungsi untuk memuat dataset GFS dari NOAA =====
@st.cache_data
def load_dataset(run_date, run_hour):
    base_url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25_1hr/gfs{run_date}/gfs_0p25_1hr_{run_hour}z"
    ds = xr.open_dataset(base_url)
    return ds

# Ambil waktu GFS otomatis
run_date, run_hour = get_latest_gfs_time()
st.sidebar.title("⚙️ Pengaturan")
st.sidebar.info(f"📅 GFS otomatis: {run_date} jam {run_hour}Z")

# Pilihan parameter
forecast_hour = st.sidebar.slider("Jam ke depan (Forecast Hour)", 0, 240, 6, step=3)
parameter = st.sidebar.selectbox("Parameter", [
    "Curah Hujan per jam (pratesfc)",
    "Suhu Permukaan (tmp2m)",
    "Angin Permukaan (ugrd10m & vgrd10m)",
    "Tekanan Permukaan Laut (prmslmsl)"
])

# Load data dari NOAA
try:
    ds = load_dataset(run_date, run_hour)
    st.success("✅ Dataset GFS berhasil dimuat dari server NOAA.")
except Exception as e:
    st.error(f"❌ Gagal memuat data GFS: {e}")
    st.stop()

# Pemrosesan parameter
is_contour = False
is_vector = False

if "pratesfc" in parameter:
    var = ds["pratesfc"][forecast_hour, :, :] * 3600
    label = "Curah Hujan (mm/jam)"
    cmap = "Blues"
elif "tmp2m" in parameter:
    var = ds["tmp2m"][forecast_hour, :, :] - 273.15
    label = "Suhu (°C)"
    cmap = "coolwarm"
elif "ugrd10m" in parameter:
    u = ds["ugrd10m"][forecast_hour, :, :]
    v = ds["vgrd10m"][forecast_hour, :, :]
    speed = (u**2 + v**2)**0.5 * 1.94384
    var = speed
    label = "Kecepatan Angin (knot)"
    cmap = plt.cm.get_cmap("RdYlGn_r", 10)
    is_vector = True
elif "prmsl" in parameter:
    var = ds["prmslmsl"][forecast_hour, :, :] / 100
    label = "Tekanan Permukaan Laut (hPa)"
    cmap = "cool"
    is_contour = True
else:
    st.warning("Parameter tidak dikenali.")
    st.stop()

# === Filter Wilayah Fokus Krayan ===
# Lintang: 2.0° hingga 4.5° LU, Bujur: 114.5° - 116.5° BT
lat_min, lat_max = 2.0, 4.5
lon_min, lon_max = 114.5, 116.5

var = var.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))
if is_vector:
    u = u.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))
    v = v.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))

# Visualisasi Peta Wilayah Krayan
fig = plt.figure(figsize=(8, 6))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

valid_time = ds.time[forecast_hour].values
valid_dt = pd.to_datetime(str(valid_time))
valid_str = valid_dt.strftime("%HUTC %a %d %b %Y")
tstr = f"t+{forecast_hour:03d}"

ax.set_title(f"{label}\nValid {valid_str}", loc="left", fontsize=10, fontweight="bold")
ax.set_title(f"GFS {run_date} {run_hour}Z {tstr}", loc="right", fontsize=10, fontweight="bold")

if is_contour:
    cs = ax.contour(var.lon, var.lat, var.values, levels=15, colors='black', linewidths=0.8, transform=ccrs.PlateCarree())
    ax.clabel(cs, fmt="%d", colors='black', fontsize=8)
else:
    im = ax.pcolormesh(var.lon, var.lat, var.values, cmap=cmap, transform=ccrs.PlateCarree())
    cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
    cbar.set_label(label)
    if is_vector:
        ax.quiver(var.lon[::2], var.lat[::2], u.values[::2, ::2], v.values[::2, ::2],
                  transform=ccrs.PlateCarree(), scale=700, width=0.002, color='black')

# Tambahan geospasial
ax.coastlines(resolution='10m', linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linestyle=':')
ax.add_feature(cfeature.LAND, facecolor='lightgray')

st.pyplot(fig)
