

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { appId, webhookUrl } = req.body;

  if (!appId) {
    return res.status(400).json({ error: 'appId is required' });
  }

  if (!webhookUrl) {
    return res.status(400).json({ error: 'webhookUrl is required' });
  }

  try {
    // Fetch app info from Meta/Oculus Graph API
    const response = await fetch(
      `https://graph.oculus.com/graphql?forced_locale=en_US&doc_id=5303836509676156&variables={"applicationID":"${appId}","hmdType":"HOLLYWOOD","firstStoreItems":1,"releaseChannels":["LIVE"]}`,
      {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch app data from Meta API');
    }

    const data = await response.json();

    const appData = data?.data?.node;
    if (!appData) {
      return res.status(404).json({ error: 'App not found' });
    }

    const appName = appData.displayName || 'Unknown App';
    const versionCode = appData.primaryBinary?.version || 'Unknown';
    const versionString = appData.primaryBinary?.versionString || 'Unknown';
    const releaseDate = appData.primaryBinary?.created_date || Date.now() / 1000;
    const fileSize = appData.primaryBinary?.size || 0;

    const updateInfo = {
      appId,
      appName,
      versionCode,
      versionString,
      releaseDate: new Date(releaseDate * 1000).toISOString(),
      fileSize: (fileSize / 1024 / 1024 / 1024).toFixed(2) + ' GB'
    };

    const discordPayload = {
      embeds: [{
        title: 'Update Checker,
        description: `**${appName}** has a got a new update`,
        color: 5814783,
        fields: [
          {
            name: 'App Name',
            value: appName,
            inline: true
          },
          {
            name: 🆔App ID',
            value: appId,
            inline: true
          },
          {
            name: 'Version',
            value: versionString,
            inline: true
          },
          {
            name: 'Version Code',
            value: versionCode.toString(),
            inline: true
          },
          {
            name: 'File Size',
            value: updateInfo.fileSize,
            inline: true
          },
          {
            name: 'Release Date',
            value: `<t:${Math.floor(releaseDate)}:F>`,
            inline: false
          }
        ],
        footer: {
          text: 'Meta Update Checker'
        },
        timestamp: new Date().toISOString()
      }]
    };

    const webhookResponse = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(discordPayload)
    });

    if (!webhookResponse.ok) {
      throw new Error('Failed to send Discord webhook');
    }

    return res.status(200).json({
      success: true,
      data: updateInfo,
      message: 'Update checked and Discord notification sent'
    });

  } catch (error) {
    console.error('Error:', error);
    return res.status(500).json({
      error: error.message || 'Internal server error'
    });
  }
}
