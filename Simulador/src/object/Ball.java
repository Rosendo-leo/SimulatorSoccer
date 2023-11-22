package object;

import java.awt.image.BufferedImage;

public class Ball extends Object{
	
	private BufferedImage sprite;

	public Ball(int x, int y, int width, int height, BufferedImage sprite) {
		super(x, y, width, height, sprite);
		this.sprite = sprite;
	}
	
	public void tick(){
		
	}

}
