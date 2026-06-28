import Foundation

func getBlueLightClient() -> AnyObject? {
    guard let bundle = Bundle(path: "/System/Library/PrivateFrameworks/CoreBrightness.framework") else {
        print("ERROR: Cannot load CoreBrightness.framework")
        return nil
    }
    bundle.load()
    guard let CBClient = NSClassFromString("CBClient") as? NSObject.Type else {
        print("ERROR: Cannot find CBClient class")
        return nil
    }
    let client = CBClient.init()
    return client.perform(NSSelectorFromString("blueLightClient"))!.takeUnretainedValue()
}

guard let bl = getBlueLightClient() else { exit(1) }

let mode = 0 as NSNumber       // 0 = manual (schedule won't override)
let enabled = true as NSNumber
let strength = 1.0 as NSNumber
let commit = true as NSNumber

let _ = bl.perform(NSSelectorFromString("setMode:"), with: mode)
let _ = bl.perform(NSSelectorFromString("setEnabled:"), with: enabled)
let _ = bl.perform(NSSelectorFromString("setStrength:commit:"), with: strength, with: commit)

print("Night Shift → manual mode, always ON, strength 1.0")
