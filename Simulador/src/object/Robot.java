package object;

import java.awt.Graphics;
import java.awt.image.BufferedImage;

public class Robot extends Object{
	
	private BufferedImage sprite;
	private boolean enemy;

	public Robot(int x, int y, int width, int height, BufferedImage sprite, boolean enemy) {
		super(x, y, width, height, sprite);
		this.sprite = sprite;
		this.enemy = enemy;
	}
	
	public void tick() {
		
	}

}
