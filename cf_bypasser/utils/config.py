import random
from typing import Optional, Dict

OPERATING_SYSTEMS = ["windows", "macos", "linux"]

SCREEN_RESOLUTIONS = [
    (1920, 1080), (1920, 1200), (2560, 1440), (1680, 1050),
    (1600, 900), (1366, 768), (1440, 900), (1536, 864),
    (2560, 1600), (3840, 2160)
]


class BrowserConfig:
    """Generate random browser configurations with integrated UA generation."""
        
    @staticmethod
    def get_firefox_headers() -> Dict[str, str]:
        """Get Firefox-specific headers."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    @staticmethod
    def generate_random_config(
        selected_os: Optional[str] = None, 
        firefox_version: int = None, 
        lang: str = "en-US"
    ) -> Dict:
        """Generate random browser configuration based on OS."""
        
        if selected_os is None or selected_os not in OPERATING_SYSTEMS:
            selected_os = random.choice(OPERATING_SYSTEMS)
        
        if firefox_version is None:
            firefox_version = random.randint(140, 145) # Recent Firefox versions
        
        # Random screen resolution
        screen_width, screen_height = random.choice(SCREEN_RESOLUTIONS)
        
        # Calculate inner dimensions (subtract browser chrome)
        toolbar_height = random.randint(70, 100)
        inner_width = screen_width
        inner_height = screen_height - toolbar_height
        
        # Random history length
        history_length = random.randint(2, 8)
        
        # Random hardware cores (realistic values)
        hardware_cores = random.choice([2, 4, 6, 8, 12, 16, 20, 24])
        
        # Language configuration
        languages = [lang]
        if lang != "en-US" and not lang.startswith("en"):
            languages.append("en-US")
        
        config = {
            'window.outerHeight': screen_height,
            'window.outerWidth': screen_width,
            'window.innerHeight': inner_height,
            'window.innerWidth': inner_width,
            'window.history.length': history_length,
            'navigator.appCodeName': 'Mozilla',
            'navigator.appName': 'Netscape',
            'navigator.hardwareConcurrency': hardware_cores,
            'navigator.product': 'Gecko',
            'navigator.productSub': '20100101',
            'navigator.language': lang,
            'navigator.languages': languages,
        }
        
        # OS-specific configurations
        if selected_os == "windows":
            return BrowserConfig._configure_windows(config, firefox_version)
        elif selected_os == "macos":
            return BrowserConfig._configure_macos(config, firefox_version)
        elif selected_os == "linux":
            return BrowserConfig._configure_linux(config, firefox_version)
        
        return config
    
    @staticmethod
    def _configure_windows(config: Dict, firefox_version: int) -> Dict:
        """Configure Windows-specific browser settings."""
        win_versions = [
            "Windows NT 10.0; Win64; x64",
            "Windows NT 11.0; Win64; x64",
        ]
        win_version = random.choice(win_versions)
        
        config.update({
            'navigator.userAgent': f'Mozilla/5.0 ({win_version}; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0',
            'navigator.appVersion': f'5.0 ({win_version})',
            'navigator.oscpu': win_version,
            'navigator.platform': 'Win32',
            'navigator.maxTouchPoints': random.choice([0, 10]),
        })
        return config
    
    @staticmethod
    def _configure_macos(config: Dict, firefox_version: int) -> Dict:
        """Configure macOS-specific browser settings."""
        macos_versions = [
            ("13_0", "13.0"),  # Ventura
            ("14_0", "14.0"),  # Sonoma
            ("15_0", "15.0"),  # Sequoia
        ]
        mac_ver_underscore, mac_ver_dot = random.choice(macos_versions)
        
        config.update({
            'navigator.userAgent': f'Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ver_underscore}; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0',
            'navigator.appVersion': f'5.0 (Macintosh)',
            'navigator.oscpu': f'Intel Mac OS X {mac_ver_dot}',
            'navigator.platform': 'MacIntel',
            'navigator.maxTouchPoints': 0,
        })
        return config
    
    @staticmethod
    def _configure_linux(config: Dict, firefox_version: int) -> Dict:
        """Configure Linux-specific browser settings."""
        linux_distros = [
            "X11; Linux x86_64",
            "X11; Ubuntu; Linux x86_64", 
            "X11; Fedora; Linux x86_64",
            "X11; Debian; Linux x86_64",
            "X11; CentOS; Linux x86_64",
            "X11; Arch Linux; Linux x86_64",
            "X11; openSUSE; Linux x86_64",
            "X11; Manjaro; Linux x86_64",
        ]
        linux_distro = random.choice(linux_distros)
        
        config.update({
            'navigator.userAgent': f'Mozilla/5.0 ({linux_distro}; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0',
            'navigator.appVersion': '5.0 (X11)',
            'navigator.oscpu': 'Linux x86_64',
            'navigator.platform': 'Linux x86_64',
            'navigator.maxTouchPoints': 0,
        })
        return config


# Maintain backward compatibility
def generate_random_config(selected_os: Optional[str] = None, firefox_version: int = None, lang: str = "en-US") -> dict:
    """Generate random browser configuration based on OS (backward compatibility function)."""
    return BrowserConfig.generate_random_config(selected_os, firefox_version, lang)