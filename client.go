//go:build windows
// +build windows

package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"golang.org/x/sys/windows/registry"
)

const (
	settingsPath = `Software\Microsoft\Windows\CurrentVersion\Internet Settings`
	maxAttempts  = 30
	delay        = 5 * time.Second
)

func getIPFromAPI() (string, error) {
	for attempt := 0; attempt < maxAttempts; attempt++ {
		resp, err := http.Get("http://192.168.0.105:5000/get_ip")
		if err != nil {
			fmt.Printf("Error fetching IP (attempt %d): %v\n", attempt+1, err)
			if attempt < maxAttempts-1 {
				fmt.Printf("Waiting %v before next attempt...\n", delay)
				time.Sleep(delay)
			}
			continue
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			if resp.StatusCode == http.StatusNotFound {
				fmt.Printf("Resource not found (404) on attempt %d\n", attempt+1)
			} else {
				fmt.Printf("Received non-OK status code: %d on attempt %d\n", resp.StatusCode, attempt+1)
			}
			if attempt < maxAttempts-1 {
				fmt.Printf("Waiting %v before next attempt...\n", delay)
				time.Sleep(delay)
			}
			continue
		}

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return "", fmt.Errorf("error reading response body: %v", err)
		}

		var result map[string]interface{}
		err = json.Unmarshal(body, &result)
		if err != nil {
			return "", fmt.Errorf("error parsing JSON response: %v", err)
		}

		if ip, ok := result["ip"].(string); ok && ip != "" {
			fmt.Printf("Successfully retrieved IP on attempt %d: %s\n", attempt+1, ip)
			return ip, nil
		}
	}

	return "", fmt.Errorf("failed to retrieve IP after %d attempts", maxAttempts)
}

func setRegistryValue(name string, value interface{}) error {
	key, err := registry.OpenKey(registry.CURRENT_USER, settingsPath, registry.ALL_ACCESS)
	if err != nil {
		return fmt.Errorf("error opening registry key: %v", err)
	}
	defer key.Close()

	switch v := value.(type) {
	case string:
		err = key.SetStringValue(name, v)
	case uint32:
		err = key.SetDWordValue(name, v)
	default:
		return fmt.Errorf("unsupported value type")
	}

	if err != nil {
		return fmt.Errorf("error setting registry value: %v", err)
	}
	return nil
}

func getRegistryValue(name string) (interface{}, error) {
	key, err := registry.OpenKey(registry.CURRENT_USER, settingsPath, registry.QUERY_VALUE)
	if err != nil {
		return nil, fmt.Errorf("error opening registry key: %v", err)
	}
	defer key.Close()

	dwordValue, _, err := key.GetIntegerValue(name)
	if err == nil {
		return uint32(dwordValue), nil
	}

	stringValue, _, err := key.GetStringValue(name)
	if err == nil {
		return stringValue, nil
	}

	if err == registry.ErrNotExist {
		return nil, nil
	}

	return nil, fmt.Errorf("error getting registry value: %v", err)
}

func updateProxyEnable() error {
	proxyEnable, err := getRegistryValue("ProxyEnable")
	if err != nil {
		return fmt.Errorf("error getting ProxyEnable: %v", err)
	}

	switch v := proxyEnable.(type) {
	case uint32:
		if v != 1 {
			if err := setRegistryValue("ProxyEnable", uint32(1)); err != nil {
				return fmt.Errorf("error setting ProxyEnable: %v", err)
			}
			fmt.Println("ProxyEnable set to 1")
		} else {
			fmt.Println("ProxyEnable already set to 1")
		}
	case string:
		if v != "1" {
			if err := setRegistryValue("ProxyEnable", uint32(1)); err != nil {
				return fmt.Errorf("error setting ProxyEnable: %v", err)
			}
			fmt.Println("ProxyEnable set to 1")
		} else {
			fmt.Println("ProxyEnable already set to 1")
		}
	default:
		fmt.Printf("Unexpected ProxyEnable type: %T. Setting to 1.\n", v)
		if err := setRegistryValue("ProxyEnable", uint32(1)); err != nil {
			return fmt.Errorf("error setting ProxyEnable: %v", err)
		}
	}

	return nil
}

func updateProxyServer() error {
	currentProxy, err := getRegistryValue("ProxyServer")
	if err != nil {
		return fmt.Errorf("error getting ProxyServer: %v", err)
	}

	currentProxyStr, ok := currentProxy.(string)
	if !ok || currentProxyStr == "" || strings.HasPrefix(currentProxyStr, "127.0.0.1") {
		ip, err := getIPFromAPI()
		if err != nil {
			return fmt.Errorf("failed to get new IP: %v", err)
		}

		newProxyServer := fmt.Sprintf("%s:8081", ip)
		err = setRegistryValue("ProxyServer", newProxyServer)
		if err != nil {
			return fmt.Errorf("error setting ProxyServer: %v", err)
		}

		fmt.Printf("ProxyServer updated to %s\n", newProxyServer)
	} else {
		fmt.Printf("ProxyServer is already set to a non-localhost value: %s\n", currentProxyStr)
	}

	return nil
}

func main() {
	if err := updateProxyEnable(); err != nil {
		fmt.Println(err)
	}

	if err := updateProxyServer(); err != nil {
		fmt.Println(err)
	}
}
