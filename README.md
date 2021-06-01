# pydis-pixels
Python Discord server thing

https://pixels.pythondiscord.com/info/
## Usage
Get your token from here https://pixels.pythondiscord.com/info/authentication

Create `config.json` from `config.template.json` and fill in your token.
### Your own images
Add your image to the `imgs` folder.

You should name it    
name,scalex,(x,y).png    
e.g.    
jmcb,10x,(75,2).png

Then add it to `imgs` at the top of `main.py`.

### Discord bot component
First get a bot token and put it in the config. This will automatically run the bot. Add the bot to your server and run `pixels.startmirror {channel}`. Put the resulting message ID and channel ID into your config, and you're good to go.

## Compendium
A source for every image on the canvas in one place.    
https://jmcb17.github.io/pydis-pixels/pages/    
https://github.com/JMcB17/pydis-pixels/blob/github-pages/pages/README.md
