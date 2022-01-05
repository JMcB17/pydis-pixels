# pydis-pixels

A client for the Python Discord's Pixels event, an API-based r/place style thing.

https://pixels.pythondiscord.com/info/

I'm now repurposing it to work with different apis, specifically my friend's new project cmpc pixels

## Usage
Get your token from here https://pixels.pythondiscord.com/info/authentication

Create `config.json` from `config.template.json` and fill in your token.

Install dependencies

Then run

### Your own images
Add your image to the `images` folder.

You should name it    
name,scalex,(x,y).png    
e.g.    
jmcb,10x,(75,2).png

### Discord bot component
First get a bot token and put it in the config. This will automatically run the bot. Add the bot to your server and run `pixels.startmirror {channel}`. Put the resulting message ID and channel ID into your config, and you're good to go.

## Compendium
A source for every image on the canvas in one place.    
https://joelsgp.github.io/pixels-client/pages/    
https://github.com/joelsgp/pixels-client/blob/github-pages/pages/README.md
