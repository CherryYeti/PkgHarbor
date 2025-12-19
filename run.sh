flatpak install flathub org.gnome.Platform//49 org.gnome.Sdk//49
flatpak-builder --user --install --force-clean build-dir com.cherryyeti.PkgHarbor.json
flatpak run com.cherryyeti.PkgHarbor 