from linker_engine.planning.geographic import GeographicBridge,GeographicReference
from linker_engine.planning.errors import InvalidInput
reference=GeographicReference(schema_version=1,method="wgs84_cart_topocentric_v1",longitude_deg=0,latitude_deg=90,ellipsoid_height_m=0,height_basis="known_wgs84_ellipsoid")
try:print(GeographicBridge(reference).inverse(0,0,2**53-1))
except InvalidInput as error:print(type(error).__name__+": "+str(error))
