import fetch from "node-fetch";

const WEBHOOK_URL = "https://discord.com/api/webhooks/1424841892327194779/hq6Gv02IvTHm8x35fhHW6Z0fknKB2g4OJIa4dOIpPSYCgoDR9hHpILZHPFdIAs0cSL-M";
const APP_IDS = ["4979055762136823", "8485526434899813"];
const GITHUB_REPO = "Real1w/UpdateLoader"; 
const FILE_PATH = "data/lastVersions.json";

export default async function handler(req, res) {
  try {
    const fileRes = await fetch(
      `https://api.github.com/repos/${GITHUB_REPO}/contents/${FILE_PATH}`,
      {
        headers: { Authorization: `token ${GITHUB_TOKEN}` },
      }
    );
    const fileData = await fileRes.json();
    const oldContent = Buffer.from(fileData.content, "base64").toString("utf8");
    let lastVersions = JSON.parse(oldContent || "{}");

    let updates = [];

    for (const appid of APP_IDS) {
      const response = await fetch(
        `https://graph.oculus.com/${appid}?fields=latest_supported_binary{id,version,change_log,created_date,version_code}&access_token=OC|200760620292815|`
      );
      const data = await response.json();

      if (!data.latest_supported_binary) continue;
      const binary = data.latest_supported_binary;
      const version = binary.version;
      const changelog = binary.change_log || "No changelog.";
      const date = binary.created_date || "Unknown";

      if (lastVersions[appid] !== version) {
        updates.push({ appid, version, changelog, date });
        lastVersions[appid] = version;

        await fetch(WEBHOOK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: "Meta Update Checker",
            embeds: [
              {
                title: "🆕 Update Found",
                color: 0x00ffcc,
                fields: [
                  { name: "App ID", value: appid, inline: true },
                  { name: "Version", value: version, inline: true },
                  { name: "Date", value: date, inline: true },
                  {
                    name: "Changelog",
                    value: changelog.substring(0, 1024),
                  },
                ],
                footer: { text: "From GitHub Persistent Checker" },
                timestamp: new Date().toISOString(),
              },
            ],
          }),
        });
      }
    }

    const updatedContent = Buffer.from(JSON.stringify(lastVersions, null, 2)).toString("base64");

    await fetch(
      `https://api.github.com/repos/${GITHUB_REPO}/contents/${FILE_PATH}`,
      {
        method: "PUT",
        headers: {
          Authorization: `token ${GITHUB_TOKEN}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: "Update Meta app versions",
          content: updatedContent,
          sha: fileData.sha,
        }),
      }
    );

    return res.status(200).json({ message: "Done", updates });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: e.message });
  }
}
